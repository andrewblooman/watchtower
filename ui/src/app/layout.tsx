import "./globals.css";
import type { Metadata } from "next";

export const metadata: Metadata = {
  title: "AI Reliability Engineer Platform (Prototype)",
  description: "Persistent SRE agent dashboard prototype"
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <body className="min-h-screen app-bg">{children}</body>
    </html>
  );
}

