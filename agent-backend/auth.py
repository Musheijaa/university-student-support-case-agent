"""Minimal, explicit authorization for Week 4 tool calls.

This is NOT a real authentication system - there is no login, no
password, no token verification. It exists only to give tool
authorization rules (see docs/tool-catalogue.md) something concrete to
check, as required by the Week 4 brief. A caller's role is taken
directly from a request header and trusted as-is.

Real authentication (verifying who a caller actually is) is out of
scope until a later phase; do not treat this as a security boundary
against a malicious client - it only distinguishes cooperating callers
for the purposes of this bounded academic demonstration.
"""

from typing import Literal

from fastapi import Header
from pydantic import BaseModel

Role = Literal["student", "staff", "guest"]


class Actor(BaseModel):
    role: Role
    user_id: str


def get_actor(
    x_user_role: str = Header(default="student", alias="X-User-Role"),
    x_user_id: str = Header(default="anonymous", alias="X-User-Id"),
) -> Actor:
    role: Role = x_user_role if x_user_role in ("student", "staff", "guest") else "guest"
    return Actor(role=role, user_id=x_user_id)
