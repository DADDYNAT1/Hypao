import "./globals.css";

export const metadata = {
  title: "PFP Sticker Composer",
  description: "Place a sticker on your PFP with background auto-removed",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <body>{children}</body>
    </html>
  );
}
