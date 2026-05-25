"use client";

import { createContext, useContext, useState, ReactNode } from "react";
import type { UserKey } from "@/lib/demo-data";

type Ctx = { user: UserKey; setUser: (u: UserKey) => void };
const UserCtx = createContext<Ctx>({ user: "junior", setUser: () => {} });

export function UserProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<UserKey>("junior");
  return <UserCtx.Provider value={{ user, setUser }}>{children}</UserCtx.Provider>;
}

export function useUser() {
  return useContext(UserCtx);
}
