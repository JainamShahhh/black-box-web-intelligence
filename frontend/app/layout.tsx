import type { Metadata } from 'next';
import Link from 'next/link';
import './globals.css';

export const metadata: Metadata = {
  title: 'Black-Box Web Intelligence',
  description: 'Autonomous multi-agent system for reverse-engineering backend APIs through intelligent UI analysis',
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en">
      <body className="min-h-screen bg-background text-foreground cyber-grid">
        <div className="min-h-screen flex flex-col">
          {/* Header */}
          <header className="border-b border-border bg-card/95 backdrop-blur-sm sticky top-0 z-50">
            <div className="container mx-auto px-4 py-3 flex items-center justify-between">
              <Link href="/" className="flex items-center space-x-3 group">
                <div className="w-10 h-10 rounded-lg bg-primary/20 flex items-center justify-center glow-primary group-hover:scale-105 transition-transform">
                  <span className="text-primary font-display font-bold text-xl">B</span>
                </div>
                <div>
                  <h1 className="font-display font-bold text-lg text-primary">
                    Black-Box Web Intelligence
                  </h1>
                  <p className="text-xs text-foreground/50">
                    Agentic API Discovery System
                  </p>
                </div>
              </Link>
              
              <nav className="flex items-center space-x-6">
                <Link 
                  href="/" 
                  className="text-sm text-foreground/70 hover:text-primary transition-colors flex items-center space-x-1"
                >
                  <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M3 12l2-2m0 0l7-7 7 7M5 10v10a1 1 0 001 1h3m10-11l2 2m-2-2v10a1 1 0 01-1 1h-3m-6 0a1 1 0 001-1v-4a1 1 0 011-1h2a1 1 0 011 1v4a1 1 0 001 1m-6 0h6" />
                  </svg>
                  <span>Dashboard</span>
                </Link>
                <a 
                  href="http://localhost:8000/docs" 
                  target="_blank"
                  rel="noopener noreferrer"
                  className="text-sm text-foreground/70 hover:text-primary transition-colors flex items-center space-x-1"
                >
                  <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
                  </svg>
                  <span>API Docs</span>
                </a>
                <a 
                  href="https://github.com" 
                  target="_blank"
                  rel="noopener noreferrer"
                  className="text-sm text-foreground/70 hover:text-primary transition-colors flex items-center space-x-1"
                >
                  <svg className="w-4 h-4" fill="currentColor" viewBox="0 0 24 24">
                    <path d="M12 0c-6.626 0-12 5.373-12 12 0 5.302 3.438 9.8 8.207 11.387.599.111.793-.261.793-.577v-2.234c-3.338.726-4.033-1.416-4.033-1.416-.546-1.387-1.333-1.756-1.333-1.756-1.089-.745.083-.729.083-.729 1.205.084 1.839 1.237 1.839 1.237 1.07 1.834 2.807 1.304 3.492.997.107-.775.418-1.305.762-1.604-2.665-.305-5.467-1.334-5.467-5.931 0-1.311.469-2.381 1.236-3.221-.124-.303-.535-1.524.117-3.176 0 0 1.008-.322 3.301 1.23.957-.266 1.983-.399 3.003-.404 1.02.005 2.047.138 3.006.404 2.291-1.552 3.297-1.23 3.297-1.23.653 1.653.242 2.874.118 3.176.77.84 1.235 1.911 1.235 3.221 0 4.609-2.807 5.624-5.479 5.921.43.372.823 1.102.823 2.222v3.293c0 .319.192.694.801.576 4.765-1.589 8.199-6.086 8.199-11.386 0-6.627-5.373-12-12-12z"/>
                  </svg>
                  <span>Source</span>
                </a>
              </nav>
            </div>
          </header>

          {/* Main Content */}
          <main className="flex-1">
            {children}
          </main>

          {/* Footer */}
          <footer className="border-t border-border py-4 bg-card/50">
            <div className="container mx-auto px-4">
              <div className="flex flex-col md:flex-row items-center justify-between space-y-2 md:space-y-0">
                <p className="text-xs text-foreground/40">
                  <span className="text-primary font-medium">Scientific Loop:</span>{' '}
                  Explore → Observe → Infer → Critique → Probe → Update → Repeat
                </p>
                <div className="flex items-center space-x-4 text-xs text-foreground/40">
                  <span>Powered by LangGraph + Playwright</span>
                  <span>•</span>
                  <span>GPT-4o / Claude 3.5</span>
                </div>
              </div>
            </div>
          </footer>
        </div>
      </body>
    </html>
  );
}
