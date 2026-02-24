import { Inter, Libre_Baskerville } from "next/font/google";

// Inter for body text, labels, table content, stats
export const inter = Inter({
  subsets: ["latin"],
  variable: "--font-inter",
});

// Libre Baskerville as the web-safe equivalent of Baskerville
// Used for titles, headers, logo
export const baskerville = Libre_Baskerville({
  subsets: ["latin"],
  weight: ["400", "700"],
  style: ["normal", "italic"],
  variable: "--font-baskerville",
});
