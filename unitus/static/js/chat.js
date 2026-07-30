/*
 * Unitus - Chat Module
 * Handles WebSocket messaging, live read receipts, keyset pagination,
 * and conversation deletion for the chat pages (inbox / room / new-direct).
 */

document.addEventListener('DOMContentLoaded', () => {
    initConversationDelete();

    const chatHistory = document.getElementById('chatHistory');
    if (chatHistory) {
        new ChatRoomController(chatHistory);
    }

    const sidebar = document.querySelector('.chat-list-body');
    if (sidebar) {
        new SidebarNotifier(sidebar);
    }
});

// ---------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------

function getCookie(name) {
    const match = document.cookie.match('(^|;)\\s*' + name + '\\s*=\\s*([^;]+)');
    return match ? decodeURIComponent(match[2]) : null;
}

function formatTime(isoString) {
    return new Date(isoString).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', hour12: false });
}

function formatDayLabel(isoString) {
    const date = new Date(isoString);
    const today = new Date();
    const yesterday = new Date();
    yesterday.setDate(today.getDate() - 1);

    const isSameDay = (a, b) =>
        a.getFullYear() === b.getFullYear() && a.getMonth() === b.getMonth() && a.getDate() === b.getDate();

    if (isSameDay(date, today)) return 'Today';
    if (isSameDay(date, yesterday)) return 'Yesterday';
    return date.toLocaleDateString([], { year: 'numeric', month: 'short', day: 'numeric' });
}

// ---------------------------------------------------------------------
// Sidebar: delete / leave a conversation
// ---------------------------------------------------------------------

function initConversationDelete() {
    document.querySelectorAll('[data-delete-room]').forEach((btn) => {
        btn.addEventListener('click', (e) => {
            e.preventDefault();
            e.stopPropagation();

            const roomId = btn.getAttribute('data-delete-room');
            if (!confirm('Delete this conversation? It will be removed from your inbox only.')) {
                return;
            }

            fetch(`/chat/room/${roomId}/delete/`, {
                method: 'POST',
                headers: { 'X-CSRFToken': getCookie('csrftoken') },
            })
                .then((res) => {
                    if (!res.ok) throw new Error('Delete failed');
                    const item = btn.closest('.chat-item');
                    if (item) item.remove();

                    const chatHistory = document.getElementById('chatHistory');
                    if (chatHistory && chatHistory.getAttribute('data-room-id') === roomId) {
                        window.location.href = '/chat/';
                    }
                })
                .catch((err) => console.error('[Unitus Chat] Failed to delete conversation:', err));
        });
    });
}

// ---------------------------------------------------------------------
// Main chat room controller
// ---------------------------------------------------------------------

class ChatRoomController {
    constructor(container) {
        this.container = container;
        this.mode = container.getAttribute('data-mode');             // 'room' | 'new-direct'
        this.currentUserId = container.getAttribute('data-current-user-id');
        this.wsPath = container.getAttribute('data-ws-path');

        this.oldestLoadedId = container.getAttribute('data-oldest-loaded-id') || null;
        this.roomId = container.getAttribute('data-room-id') || null;
        this.isLoadingOlder = false;
        this.hasMoreOlder = true;

        this.form = document.getElementById('chatInputArea');
        this.input = document.getElementById('chatInput');
        this.loadOlderBtn = document.getElementById('loadOlderBtn');

        this._connectSocket();
        this._bindSendForm();
        this._bindPagination();
        this._insertDayDividers();

        this.container.scrollTop = this.container.scrollHeight;
    }

    _connectSocket() {
        const scheme = window.location.protocol === 'https:' ? 'wss://' : 'ws://';
        this.socket = new WebSocket(scheme + window.location.host + this.wsPath);

        this.socket.onmessage = (event) => {
            const data = JSON.parse(event.data);
            if (data.action === 'new_message') {
                this._handleIncomingMessage(data.message);
            } else if (data.action === 'read_receipt') {
                this._handleReadReceipt(data);
            }
        };

        this.socket.onclose = () => console.warn('[Unitus Chat] WebSocket disconnected.');
    }

    _bindSendForm() {
        if (!this.form || !this.input) return;

        this.form.addEventListener('submit', (e) => {
            e.preventDefault();
            const content = this.input.value.trim();
            if (!content) return;

            const clientRef = `c${Date.now()}${Math.random().toString(16).slice(2)}`;

            // Render immediately — don't wait for the server/WebSocket echo.
            this._renderMessage({
                id: null,
                sender: { id: Number(this.currentUserId) },
                content: content,
                sent_at: new Date().toISOString(),
            }, false, clientRef);
            this.container.scrollTop = this.container.scrollHeight;
            this._insertDayDividers();

            this.socket.send(JSON.stringify({ action: 'send_message', content, client_ref: clientRef }));
            this.input.value = '';
        });

        this.input.addEventListener('keydown', (e) => {
            if (e.key === 'Enter' && !e.shiftKey) {
                e.preventDefault();
                this.form.requestSubmit();
            }
        });
    }

    _bindPagination() {
        if (this.mode !== 'room' || !this.loadOlderBtn) return;

        this.loadOlderBtn.style.display = 'block';
        this.loadOlderBtn.addEventListener('click', () => this._loadOlderMessages());

        this.container.addEventListener('scroll', () => {
            if (this.container.scrollTop < 60 && this.hasMoreOlder && !this.isLoadingOlder) {
                this._loadOlderMessages();
            }
        });
    }

    _loadOlderMessages() {
        if (!this.oldestLoadedId || this.isLoadingOlder || !this.hasMoreOlder) return;

        this.isLoadingOlder = true;
        const previousHeight = this.container.scrollHeight;

        fetch(`/chat/room/${this.roomId}/messages/?before=${this.oldestLoadedId}`)
            .then((res) => res.json())
            .then((data) => {
                const older = data.messages;
                if (older.length === 0) {
                    this.hasMoreOlder = false;
                    if (this.loadOlderBtn) this.loadOlderBtn.style.display = 'none';
                    return;
                }

                older.forEach((msg) => this._renderMessage(msg, true));
                this.oldestLoadedId = older[0].id;

                this.container.scrollTop = this.container.scrollHeight - previousHeight;
                this._insertDayDividers();
            })
            .finally(() => {
                this.isLoadingOlder = false;
            });
    }

    _handleIncomingMessage(message) {
        const isMine = String(message.sender.id) === this.currentUserId;

        if (isMine && message.client_ref) {
            const optimisticBubble = this.container.querySelector(`[data-client-ref="${message.client_ref}"]`);
            if (optimisticBubble) {
                // Already rendered optimistically — just attach the real ID/timestamp.
                optimisticBubble.setAttribute('data-message-id', message.id);
                optimisticBubble.setAttribute('data-sent-at', message.sent_at);
            } else {
                this._renderMessage(message, false);
            }
        } else {
            this._renderMessage(message, false);
        }

        this.container.scrollTop = this.container.scrollHeight;
        this._insertDayDividers();

        if (this.mode === 'new-direct' && message.room_id) {
            this.roomId = message.room_id;
            this.mode = 'room';
            this.container.setAttribute('data-room-id', message.room_id);
            history.replaceState(null, '', `/chat/room/${message.room_id}/`);
        }

        if (!isMine) {
            this.socket.send(JSON.stringify({ action: 'mark_read' }));
        }
    }

    _handleReadReceipt(data) {
        if (String(data.user_id) === this.currentUserId) return;

        const readAt = new Date(data.read_at);
        this.container.querySelectorAll('.msg-bubble.msg-sent').forEach((bubble) => {
            const sentAt = new Date(bubble.getAttribute('data-sent-at'));
            if (sentAt <= readAt) {
                const tick = bubble.querySelector('.msg-tick');
                if (tick) {
                    tick.textContent = '✓✓';
                    tick.classList.remove('tick-unread');
                    tick.classList.add('tick-read');
                }
            }
        });
    }

    _renderMessage(message, prepend, clientRef) {
        const isMine = String(message.sender.id) === this.currentUserId;

        const bubble = document.createElement('div');
        bubble.className = `msg-bubble ${isMine ? 'msg-sent' : 'msg-received'}`;
        if (message.id) bubble.setAttribute('data-message-id', message.id);
        bubble.setAttribute('data-sent-at', message.sent_at);
        if (clientRef) bubble.setAttribute('data-client-ref', clientRef);

        const textSpan = document.createElement('span');
        textSpan.className = 'msg-text';
        textSpan.textContent = message.content;   // textContent -> safe against XSS
        bubble.appendChild(textSpan);

        const meta = document.createElement('div');
        meta.className = 'msg-meta';

        const timeSpan = document.createElement('span');
        timeSpan.className = 'msg-time';
        timeSpan.textContent = formatTime(message.sent_at);
        meta.appendChild(timeSpan);

        if (isMine) {
            const tick = document.createElement('span');
            tick.className = 'msg-tick tick-unread';
            tick.textContent = '✓';
            meta.appendChild(tick);
        }

        bubble.appendChild(meta);

        if (prepend) {
            const loadWrapper = this.container.querySelector('.load-more-wrapper');
            const insertBeforeNode = loadWrapper ? loadWrapper.nextSibling : this.container.firstChild;
            this.container.insertBefore(bubble, insertBeforeNode);
        } else {
            this.container.appendChild(bubble);
        }
    }

    _insertDayDividers() {
        this.container.querySelectorAll('.day-divider').forEach((el) => el.remove());

        let lastLabel = null;
        Array.from(this.container.querySelectorAll('.msg-bubble')).forEach((bubble) => {
            const label = formatDayLabel(bubble.getAttribute('data-sent-at'));
            if (label !== lastLabel) {
                const divider = document.createElement('div');
                divider.className = 'day-divider';
                const span = document.createElement('span');
                span.textContent = label;
                divider.appendChild(span);
                this.container.insertBefore(divider, bubble);
                lastLabel = label;
            }
        });
    }
}


// ---------------------------------------------------------------------
// Sidebar live-updater — keeps the conversation list current on any
// page (inbox, room, new-direct-chat) without a full reload.
// ---------------------------------------------------------------------

class SidebarNotifier {
    constructor(sidebarBody) {
        this.sidebarBody = sidebarBody;
        this._connectSocket();
    }

    _connectSocket() {
        const scheme = window.location.protocol === 'https:' ? 'wss://' : 'ws://';
        this.socket = new WebSocket(scheme + window.location.host + '/ws/chat/notify/');

        this.socket.onmessage = (event) => {
            const data = JSON.parse(event.data);
            if (data.action === 'conversation_update') {
                this._upsertConversation(data.conversation);
            }
        };

        this.socket.onclose = () => console.warn('[Unitus Chat] Notification socket disconnected.');
    }

    _upsertConversation(conv) {
        const emptyHint = this.sidebarBody.querySelector('.empty-hint');
        if (emptyHint) emptyHint.remove();

        let item = this.sidebarBody.querySelector(`.chat-item[data-room-id="${conv.room_id}"]`);
        if (!item) {
            item = this._buildItem(conv);
        } else {
            this._updateItem(item, conv);
        }

        // Move to the top, exactly like Telegram — most recent activity first.
        this.sidebarBody.insertBefore(item, this.sidebarBody.firstChild);
    }

    _updateItem(item, conv) {
        const lastMsgEl = item.querySelector('.last-msg');
        if (lastMsgEl) lastMsgEl.textContent = conv.last_message_content || 'No messages yet';

        const timeEl = item.querySelector('.chat-time');
        if (timeEl && conv.last_message_at) {
            timeEl.textContent = this._relativeTime(conv.last_message_at);
        }

        let badge = item.querySelector('.unread-badge');
        if (conv.unread_count > 0) {
            if (!badge) {
                badge = document.createElement('span');
                badge.className = 'unread-badge';
                item.querySelector('.chat-info-bottom').appendChild(badge);
            }
            badge.textContent = conv.unread_count;
        } else if (badge) {
            badge.remove();
        }
    }

    _buildItem(conv) {
        const a = document.createElement('a');
        a.href = `/chat/room/${conv.room_id}/`;
        a.className = 'chat-item';
        a.setAttribute('data-room-id', conv.room_id);

        const initial = (conv.display_name || '?').charAt(0).toUpperCase();
        const unreadHtml = conv.unread_count > 0
            ? `<span class="unread-badge">${conv.unread_count}</span>` : '';
        const timeHtml = conv.last_message_at
            ? `<span class="chat-time">${this._relativeTime(conv.last_message_at)}</span>` : '';

        a.innerHTML = `
            <div class="chat-avatar">${initial}</div>
            <div class="chat-info">
                <div class="chat-info-top">
                    <strong></strong>
                    ${timeHtml}
                </div>
                <div class="chat-info-bottom">
                    <span class="last-msg"></span>
                    ${unreadHtml}
                </div>
                ${conv.is_closed ? '<span class="closed-tag">Closed</span>' : ''}
            </div>
            <button class="chat-delete-btn" data-delete-room="${conv.room_id}" title="Delete conversation" type="button">&times;</button>
        `;

        // textContent for user-controlled strings -> safe against XSS
        a.querySelector('strong').textContent = conv.display_name;
        a.querySelector('.last-msg').textContent = conv.last_message_content || 'No messages yet';

        // Newly-added delete button needs its own click handler too.
        a.querySelector('[data-delete-room]').addEventListener('click', (e) => {
            e.preventDefault();
            e.stopPropagation();
            const roomId = e.currentTarget.getAttribute('data-delete-room');
            if (!confirm('Delete this conversation? It will be removed from your inbox only.')) return;

            fetch(`/chat/room/${roomId}/delete/`, {
                method: 'POST',
                headers: { 'X-CSRFToken': getCookie('csrftoken') },
            }).then((res) => {
                if (res.ok) a.remove();
            });
        });

        this.sidebarBody.appendChild(a); // temporary; caller moves it to the top
        return a;
    }

    _relativeTime(isoString) {
        const diffSeconds = Math.floor((Date.now() - new Date(isoString).getTime()) / 1000);
        if (diffSeconds < 60) return 'just now';
        if (diffSeconds < 3600) return `${Math.floor(diffSeconds / 60)}m ago`;
        if (diffSeconds < 86400) return `${Math.floor(diffSeconds / 3600)}h ago`;
        return `${Math.floor(diffSeconds / 86400)}d ago`;
    }
}