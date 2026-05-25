import type { Metadata } from "next";
import "./globals.css";
import { Nav } from "@/components/nav";
import { Header } from "@/components/header";
import { UserProvider } from "@/components/user-context";

export const metadata: Metadata = {
  title: "Blending Master",
  description: "경유 저온성상과 WAFI 주입량 의사결정을 지원하는 AI Agent",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="ko">
      <head>
        <link
          rel="stylesheet"
          href="https://cdn.jsdelivr.net/npm/@tabler/icons-webfont@latest/dist/tabler-icons.min.css"
        />
      </head>
      <body>
        <UserProvider>
          <div className="bm-app">
            <Header />
            <div className="bm-layout">
              <Nav />
              <div className="bm-body">{children}</div>
            </div>
          </div>
        </UserProvider>
      </body>
    </html>
  );
}
