import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "SetuAI",
  description: "Bridging the gap between project plans and real-time progress.",
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en">
      <body>{children}</body>
    </html>
  );
}
