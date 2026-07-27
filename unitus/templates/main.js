/*
 * Unitas - Main UI Controller
 * -----------------------------------------------------------
 * Handles UI interactions (Tabs, Modals, Form Submissions) for all modules.
 * Uses conditional checks to prevent null reference errors across different HTML files.
 */

document.addEventListener("DOMContentLoaded", () => {

  // ==========================================
  // 1. PROFILE MODULE
  // ==========================================
  const profileContainer = document.getElementById('viewName');
  if (profileContainer) {
    console.log("[Unitas] Profile module initialized.");

    // Handle Edit Profile Form Submission
    const editProfileSection = document.getElementById('editProfileSection');
    if (editProfileSection) {
      const form = editProfileSection.querySelector('form');
      if (form) {
        form.addEventListener('submit', (e) => {
          e.preventDefault();
          // TODO: Call saveProfile() from storage layer here
          alert('Profile information saved successfully!');
          editProfileSection.style.display = 'none';
        });
      }
    }
  }

  // ==========================================
  // 2. CHAT MODULE
  // ==========================================
  const chatHistory = document.getElementById('chatHistory');
  if (chatHistory) {
    console.log("[Unitas] Chat module initialized.");

    // Handle sending a message
    const chatInputArea = document.querySelector('.chat-input-area');
    if (chatInputArea) {
      const sendBtn = chatInputArea.querySelector('button');
      const textArea = chatInputArea.querySelector('textarea');
      
      sendBtn.addEventListener('click', () => {
        const text = textArea.value.trim();
        if (text) {
          // TODO: Call sendMessage() from storage layer here
          console.log("Message sent:", text);
          textArea.value = ''; // Clear input
        }
      });
    }
  }

  // ==========================================
  // 3. TICKET MANAGEMENT MODULE
  // ==========================================
  const ticketsList = document.getElementById('ticketsList');
  if (ticketsList) {
    console.log("[Unitas] Tickets module initialized.");

    // Handle Ticket Tabs Switching
    const ticketTabs = document.querySelectorAll('.ticket-tab');
    ticketTabs.forEach(tab => {
      tab.addEventListener('click', function() {
        ticketTabs.forEach(t => t.classList.remove('active'));
        this.classList.add('active');
        // TODO: Filter tickets list based on selected tab
      });
    });
  }

  // ==========================================
  // 4. SEARCH & DISCOVERY MODULE
  // ==========================================
  const searchResultsList = document.getElementById('searchResultsList');
  if (searchResultsList) {
    console.log("[Unitas] Search module initialized.");

    // Handle Search Tabs Switching
    const searchTabs = document.querySelectorAll('.search-tab');
    searchTabs.forEach(tab => {
      tab.addEventListener('click', function() {
        searchTabs.forEach(t => t.classList.remove('active'));
        this.classList.add('active');
        // TODO: Change search context (Projects/Ads/Users)
      });
    });

    // Handle category badges click
    const categoryBadges = document.querySelectorAll('.category-badge');
    categoryBadges.forEach(badge => {
      badge.addEventListener('click', function() {
        console.log("Filtering by category:", this.innerText);
        // TODO: Trigger search by category
      });
    });
  }

  // ==========================================
  // 5. NOTIFICATIONS MODULE
  // ==========================================
  const notificationsList = document.getElementById('notificationsList');
  if (notificationsList) {
    console.log("[Unitas] Notifications module initialized.");

    // Handle Notification Tabs Switching
    const notifTabs = document.querySelectorAll('.notification-tab');
    notifTabs.forEach(tab => {
      tab.addEventListener('click', function() {
        notifTabs.forEach(t => t.classList.remove('active'));
        this.classList.add('active');
        // TODO: Filter notifications (All/Unread/Read)
      });
    });
  }

  // ==========================================
  // 6. MATCHMAKING & RECOMMENDATIONS MODULE
  // ==========================================
  const recommendationsList = document.getElementById('recommendationsList');
  if (recommendationsList) {
    console.log("[Unitas] Matchmaking module initialized.");

    // Handle Match Tabs Switching
    const matchTabs = document.querySelectorAll('.match-tab');
    matchTabs.forEach(tab => {
      tab.addEventListener('click', function() {
        matchTabs.forEach(t => t.classList.remove('active'));
        this.classList.add('active');
        // TODO: Fetch new recommendations based on tab
      });
    });

    // Handle Preferences Form Submission
    const preferencesForm = document.getElementById('preferencesForm');
    if (preferencesForm) {
      preferencesForm.addEventListener('submit', (e) => {
        e.preventDefault();
        alert('Recommendation preferences saved!');
      });
    }
  }

  // ==========================================
  // GLOBAL MODAL HANDLERS (Optional Helper)
  // ==========================================
  // Closes any open modal when clicking outside the modal content
  const overlays = document.querySelectorAll('.modal-overlay');
  overlays.forEach(overlay => {
    overlay.addEventListener('click', function(e) {
      if (e.target === this) {
        this.style.display = 'none';
      }
    });
  });

});