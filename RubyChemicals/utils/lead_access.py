"""
utils/lead_access.py
────────────────────
Single source of truth for "who can see / manage which lead".

Rules
  • Admin / super admin             → every lead.
  • Supervisor (role in HIERARCHY_ROLES, has a `level`, has Leads access)
                                    → own leads + leads of everyone in their
                                      reporting tree (users who `reports_to`
                                      them, directly or through the chain),
                                      plus leads shared with any of them.
                                      Users with no `reports_to` and a higher
                                      level number are visible to every
                                      supervisor above them.
  • Everyone else                   → own leads + leads shared with them.

Level 1 is the top rank; larger numbers are lower in the hierarchy.
"""

from collections import defaultdict

from django.db.models import Q

# Roles that may use their `level` to see subordinates' leads.
HIERARCHY_ROLES = ('office',)


def is_admin_user(user):
    return bool(user.is_super_admin or user.role == 'admin')


def is_supervisor(user):
    return (
        not is_admin_user(user)
        and user.role in HIERARCHY_ROLES
        and getattr(user, 'level', None) is not None
        and user.has_plugin_access('can_leads')
    )


def subordinate_ids(user):
    """
    IDs of every user below `user` in the reporting tree (cached on the user
    object per request). Starts from:
      • users whose `reports_to` is `user`, and
      • unassigned users (no `reports_to`) with a higher level number,
    then walks down through each of their own reports, however deep.
    """
    if not is_supervisor(user):
        return []
    cached = getattr(user, '_lead_subordinate_ids', None)
    if cached is None:
        from UserDetail.models import User

        children = defaultdict(list)
        admin_ids = set()
        queue = []
        rows = User.objects.filter(level__isnull=False).values_list(
            'id', 'reports_to_id', 'level', 'is_super_admin', 'role'
        )
        for uid, parent_id, level, is_super, role in rows:
            if uid == user.id:
                continue
            if is_super or role == 'admin':
                admin_ids.add(uid)
            children[parent_id].append(uid)
            if parent_id is None and level > user.level:
                queue.append(uid)
        queue.extend(children.get(user.id, []))

        seen = set()
        while queue:
            uid = queue.pop()
            if uid in seen or uid == user.id:
                continue
            seen.add(uid)
            queue.extend(children.get(uid, []))

        cached = sorted(seen - admin_ids)
        user._lead_subordinate_ids = cached
    return cached


def filterable_users(user):
    """Users that appear in the 'Leads Data of' dropdown for `user`."""
    from UserDetail.models import User
    if is_admin_user(user):
        return User.objects.filter(
            Q(role='admin') | Q(can_leads=True) | Q(role='sales')
        ).exclude(id=user.id)
    return User.objects.filter(id__in=subordinate_ids(user)).filter(
        Q(can_leads=True) | Q(role='sales')
    )


def visible_leads(user, qs=None):
    """Leads `user` is allowed to see."""
    if qs is None:
        from Operations.models import Lead
        qs = Lead.objects.filter(is_active=True)
    if is_admin_user(user):
        return qs
    ids = [user.id] + subordinate_ids(user)
    return qs.filter(
        Q(created_by_id__in=ids) | Q(collaborators__id__in=ids)
    ).distinct()


def apply_user_filter(user, qs, target_user_id):
    """
    Narrow `qs` to leads owned by or shared with one user (looked up by the
    public `user_id`). Non-admins may only pick themselves or a subordinate.
    """
    from UserDetail.models import User
    target = User.objects.filter(user_id=target_user_id).first()
    if not target:
        return qs.none()
    if (
        not is_admin_user(user)
        and target.id != user.id
        and target.id not in subordinate_ids(user)
    ):
        return qs.none()
    return qs.filter(Q(created_by=target) | Q(collaborators=target)).distinct()


def can_manage_lead(user, lead):
    """Owner, admin, or a supervisor of the owner: may transfer / share / delete."""
    if is_admin_user(user):
        return True
    return lead.created_by_id == user.id or lead.created_by_id in subordinate_ids(user)


def can_access_lead(user, lead):
    """Anyone who can see the lead can update it, add call records, follow-ups…"""
    if can_manage_lead(user, lead):
        return True
    ids = [user.id] + subordinate_ids(user)
    return lead.collaborators.filter(id__in=ids).exists()


def collaborator_candidates(lead):
    """Active users that can be added as collaborators on `lead`."""
    from UserDetail.models import User
    return (
        User.objects.filter(is_active=True)
        .filter(Q(can_leads=True) | Q(role='sales') | Q(role='admin') | Q(is_super_admin=True))
        .exclude(id=lead.created_by_id)
        .exclude(id__in=lead.collaborators.values_list('id', flat=True))
        .order_by('name')
    )
