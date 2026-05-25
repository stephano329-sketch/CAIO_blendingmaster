"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { NAV } from "@/lib/demo-data";

export function Nav() {
  const pathname = usePathname();
  return (
    <nav className="bm-sidebar">
      {NAV.map((n) => {
        const active = n.id === "/" ? pathname === "/" : pathname.startsWith(n.id);
        return (
          <div key={n.id}>
            <Link href={n.id} className={`bm-nav-btn ${active ? "active" : ""}`}>
              <i className={`ti ${n.icon}`} />
              {n.label}
            </Link>
            {n.id === "/consult" && (
              <hr
                style={{
                  border: 0,
                  borderTop: "0.5px solid var(--color-border-tertiary)",
                  margin: "8px 4px",
                }}
              />
            )}
          </div>
        );
      })}
    </nav>
  );
}
