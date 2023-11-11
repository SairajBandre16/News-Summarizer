import './globals.css';
import Header from './Header';
import Providers from './Providers';

export const metadata = {
  title: 'Create Next App',
  description: 'Generated by create next app',
};

export default function RootLayout({ children }) {
  return (
    <html lang="en">
    <Providers>
      <body className="bg-gray-200 dark:bg-zinc-900 transition-all duration-700">
        <Header />
        <div className='max-w-6xl mx-auto'>
          {children}

        </div>
      </body>
      </Providers>
    </html>
  );
}
