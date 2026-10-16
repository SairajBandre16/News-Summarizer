import { Geist, Newsreader } from "next/font/google";
import Providers from "@/components/Providers";
import ReaderPanel from "@/components/ReaderPanel";
import SiteFooter from "@/components/SiteFooter";
import SiteHeader from "@/components/SiteHeader";
import { SITE_URL } from "@/lib/constants";
import { getEdition } from "@/lib/server";
import "./globals.css";

const sans = Geist({ subsets: ["latin"], variable: "--font-geist", display: "swap" });
const serif = Newsreader({
  subsets: ["latin"],
  variable: "--font-newsreader",
  style: ["normal", "italic"],
  axes: ["opsz"],
  display: "swap",
});

const description =
  "The day's top headlines with instant summaries, a 60-second daily briefing, and stories you can listen to.";

export const metadata = {
  metadataBase: new URL(SITE_URL),
  title: { default: "BlitzFeed: the news, briefed", template: "%s · BlitzFeed" },
  description,
  applicationName: "BlitzFeed",
  openGraph: { type: "website", siteName: "BlitzFeed", title: "BlitzFeed: the news, briefed", description },
  twitter: { card: "summary_large_image", title: "BlitzFeed: the news, briefed", description },
};

export const viewport = {
  themeColor: [
    { media: "(prefers-color-scheme: light)", color: "#faf8f4" },
    { media: "(prefers-color-scheme: dark)", color: "#1b1917" },
  ],
};

export default async function RootLayout({ children }) {
  const edition = await getEdition();

  return (
    <html lang="en" suppressHydrationWarning className={`${sans.variable} ${serif.variable}`}>
      <body className="min-h-dvh bg-bg font-sans text-fg antialiased">
        <Providers>
          <a href="#main" className="skip-link">
            Skip to content
          </a>
          <SiteHeader edition={edition} />
          <main id="main" className="mx-auto w-full max-w-7xl px-4 sm:px-6 lg:px-8">
            {children}
          </main>
          <SiteFooter />
          <ReaderPanel />
        </Providers>
      </body>
    </html>
  );
}
