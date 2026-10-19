"""Единая проверка ролей и доступа к фондам/пунктам."""
import os
from database import db_manager as db

USER = 0
MANAGER = 1
BOT_ADMIN = 2  # Старое значение 2 оставлено за глобальным администратором
FUND_ADMIN = 3


def global_admin_ids():
    return {int(s.strip()) for s in os.getenv('MAX_ADMINS_ID', '').split(',') if s.strip().isdigit()}


def is_global(actor):
    return bool(actor) and (actor.id in global_admin_ids() or actor.user_type == BOT_ADMIN)


def can_manage_fund(actor, fund_id):
    if not actor or not fund_id:
        return False
    if is_global(actor):
        return True
    return actor.user_type == FUND_ADMIN and actor.fund_id == int(fund_id)


def can_create_point(actor, fund_id):
    return can_manage_fund(actor, fund_id)


def can_manage_point(actor, point_id):
    if not actor or not point_id:
        return False
    point = db.get_homestay(id=int(point_id))
    if not point:
        return False
    if can_manage_fund(actor, point.fund_id):
        return True
    return actor.user_type == MANAGER and db.manager_has_point(actor.id, point.id)


def managed_points(actor):
    if not actor:
        return []
    points = db.get_all_homestays()
    if is_global(actor):
        return points
    if actor.user_type == FUND_ADMIN:
        return [h for h in points if h.fund_id == actor.fund_id]
    if actor.user_type == MANAGER:
        ids = set(db.get_manager_point_ids(actor.id))
        return [h for h in points if h.id in ids]
    return []


def can_assign_manager(actor, manager, point):
    return (bool(manager) and manager.user_type == MANAGER and bool(point)
            and can_manage_fund(actor, point.fund_id))


def can_manage_account(actor, target):
    if not actor or not target or actor.id == target.id or is_global(target):
        return False
    if is_global(actor):
        return True
    if actor.user_type != FUND_ADMIN or not actor.fund_id:
        return False
    if target.user_type == FUND_ADMIN:
        return False
    # Администратор фонда может управлять только менеджерами, связанными с его пунктами,
    # а новые (обычные) аккаунты может назначать менеджерами только в своём фонде.
    if target.user_type == USER:
        return True  # Можно назначить нового менеджера в свой фонд.
    assigned = set(db.get_manager_point_ids(target.id))
    in_fund = {p.id for p in managed_points(actor)}
    # Нельзя сменить роль менеджера с назначениями в других фондах.
    return assigned.issubset(in_fund)
