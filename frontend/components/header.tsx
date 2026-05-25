"use client";

import { USERS } from "@/lib/demo-data";
import { useUser } from "./user-context";

export function Header() {
  const { user, setUser } = useUser();
  const current = USERS.find((u) => u.value === user)!;
  return (
    <div className="bm-header">
      <div className="bm-logo">B</div>
      <div className="bm-title">Blending Master</div>
      <div className="bm-header-right">
        <div className="user-select-wrap">
          <div className="user-avatar">{current.initials}</div>
          <select
            className="user-dropdown"
            value={user}
            onChange={(e) => setUser(e.target.value as typeof user)}
          >
            {USERS.map((u) => (
              <option key={u.value} value={u.value}>
                {u.label}
              </option>
            ))}
          </select>
          <i className="ti ti-chevron-down user-chevron" />
        </div>
        <button className="bm-settings-btn">
          <i className="ti ti-settings" />
        </button>
      </div>
    </div>
  );
}
