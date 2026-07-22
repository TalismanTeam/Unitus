from django.db import migrations

# تریگر اول: بررسی وضعیت آگهی شغلی بعد از اضافه شدن یک عضو جدید
CREATE_TRIGGER_INSERT = """
CREATE TRIGGER trg_project_members_after_insert
AFTER INSERT ON projects_projectmember
FOR EACH ROW
BEGIN
    IF NEW.project_role_id IS NOT NULL AND NEW.member_status = 'ACTIVE' THEN
        UPDATE projects_jobad ja
        JOIN projects_projectrole pr ON pr.id = ja.project_role_id
        SET ja.status = CASE
            WHEN (SELECT COUNT(*) FROM projects_projectmember pm
                  WHERE pm.project_role_id = NEW.project_role_id
                  AND pm.member_status = 'ACTIVE') >= pr.capacity
            THEN 'FILLED'
            ELSE 'OPEN'
        END
        WHERE ja.project_role_id = NEW.project_role_id
        AND ja.status <> 'CANCELLED';
    END IF;
END;
"""
DROP_TRIGGER_INSERT = "DROP TRIGGER IF EXISTS trg_project_members_after_insert;"

# تریگر دوم: بررسی وضعیت آگهی شغلی بعد از تغییر وضعیت یک عضو (مثلاً استعفا یا اخراج)
CREATE_TRIGGER_UPDATE_MEMBER = """
CREATE TRIGGER trg_project_members_after_update
AFTER UPDATE ON projects_projectmember
FOR EACH ROW
BEGIN
    IF NEW.project_role_id IS NOT NULL AND (NEW.member_status <> OLD.member_status OR NEW.project_role_id <> OLD.project_role_id) THEN
        UPDATE projects_jobad ja
        JOIN projects_projectrole pr ON pr.id = ja.project_role_id
        SET ja.status = CASE
            WHEN (SELECT COUNT(*) FROM projects_projectmember pm
                  WHERE pm.project_role_id = NEW.project_role_id
                  AND pm.member_status = 'ACTIVE') >= pr.capacity
            THEN 'FILLED'
            ELSE 'OPEN'
        END
        WHERE ja.project_role_id = NEW.project_role_id
        AND ja.status <> 'CANCELLED';
    END IF;
END;
"""
DROP_TRIGGER_UPDATE_MEMBER = "DROP TRIGGER IF EXISTS trg_project_members_after_update;"

# تریگر سوم: لغو کردن آگهی‌های شغلی باز وقتی که پروژه از حالت عضوگیری خارج می‌شود
CREATE_TRIGGER_UPDATE_PROJECT = """
CREATE TRIGGER trg_projects_after_update
AFTER UPDATE ON projects_project
FOR EACH ROW
BEGIN
    IF NEW.state <> 'RECRUITING' AND OLD.state = 'RECRUITING' THEN
        UPDATE projects_jobad
        SET status = 'CANCELLED'
        WHERE project_id = NEW.id AND status = 'OPEN';
    END IF;
END;
"""
DROP_TRIGGER_UPDATE_PROJECT = "DROP TRIGGER IF EXISTS trg_projects_after_update;"


class Migration(migrations.Migration):

    dependencies = [
        ('projects', '0001_initial'),
    ]

    operations = [
        migrations.RunSQL(
            sql=CREATE_TRIGGER_INSERT,
            reverse_sql=DROP_TRIGGER_INSERT,
        ),
        migrations.RunSQL(
            sql=CREATE_TRIGGER_UPDATE_MEMBER,
            reverse_sql=DROP_TRIGGER_UPDATE_MEMBER,
        ),
        migrations.RunSQL(
            sql=CREATE_TRIGGER_UPDATE_PROJECT,
            reverse_sql=DROP_TRIGGER_UPDATE_PROJECT,
        ),
    ]