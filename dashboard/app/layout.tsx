import type { Metadata } from "next";
import { inter, baskerville } from "@/lib/fonts";
import { ThemeProvider } from "@/lib/theme";
import { ThemeScript } from "@/app/theme-script";
import { Sidebar } from "@/components/sidebar";
import "./globals.css";

export const metadata: Metadata = {
  title: "Coupang Security Remediation | Cognition",
  description: "Devin-powered security remediation orchestrator",
  icons: {
    icon: "/cognition-logo.png",
  },
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en" className={`${inter.variable} ${baskerville.variable}`} {...{ suppressHydrationWarning: true }}>
      <body className="font-sans bg-background text-foreground antialiased">
        <ThemeScript />
        <ThemeProvider>
          <div className="flex h-screen">
            <Sidebar />
            <main className="flex-1 overflow-y-auto">
              <div className="max-w-7xl mx-auto px-8 py-8">{children}</div>
            </main>
          </div>
        </ThemeProvider>
      </body>
    </html>
  );
}
