"use client";

import React, { useEffect } from 'react';
import { useRouter } from 'next/navigation';
import { useStore } from '@/lib/store';

export default function DashboardLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  const router = useRouter();
  const { sessionId } = useStore();

  // Protect dashboard routes - redirect to landing if no active session
  useEffect(() => {
    if (!sessionId) {
      router.push('/');
    }
  }, [sessionId, router]);

  // If there's no session, render nothing while redirecting to avoid hydration mismatch flashes
  if (!sessionId) {
    return null;
  }

  return (
    <div className="flex-1 w-full h-full min-h-0 overflow-y-auto bg-[var(--bg-primary)]">
      {/* We don't render the Sidebar here because it's already rendered globally in app/layout.tsx 
          Next.js app directory layouts wrap each other. The Sidebar is at the root layout 
          so it persists across all pages, including the landing page (where it hides itself). */}
      <div className="mx-auto max-w-7xl px-4 sm:px-6 lg:px-8 py-8 h-full">
        {children}
      </div>
    </div>
  );
}
