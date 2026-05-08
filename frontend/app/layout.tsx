import type { Metadata } from "next";
import { Inter, JetBrains_Mono, Syne } from "next/font/google";
import "./globals.css";
import { cn } from "@/lib/utils";
import Sidebar from "@/components/Sidebar";
import { StoreProvider } from "@/lib/store";

const inter = Inter({ 
  subsets: ["latin"],
  variable: "--font-sans",
});

const jetbrainsMono = JetBrains_Mono({
  subsets: ["latin"],
  variable: "--font-mono",
});

const syne = Syne({
  subsets: ["latin"],
  variable: "--font-display",
  weight: ["700", "800"],
});

export const metadata: Metadata = {
  title: "Coldframe — Raw data → instant intelligence",
  description: "Upload any CSV or Excel file. Get automated EDA, AI insights, NL querying, and a production-grade BI dashboard — zero code required.",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en" className="dark scroll-smooth">
      <body className={cn(
        "min-h-screen bg-[var(--bg-primary)] font-sans antialiased text-[var(--text-primary)] selection:bg-[var(--accent-cyan)] selection:text-black flex",
        inter.variable,
        jetbrainsMono.variable,
        syne.variable
      )}>
        <StoreProvider>
          <Sidebar />
          <main className="flex-1 min-w-0 flex flex-col h-screen overflow-y-auto">
            {children}
          </main>
        </StoreProvider>
      </body>
    </html>
  );
}
