import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "AfterCare Dashboard",
  description: "Post-discharge patient follow-up monitoring",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en">
      <body>{children}</body>
    </html>
  );
}
