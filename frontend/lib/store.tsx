"use client";

import React, { createContext, useContext, useState, ReactNode } from 'react';

interface StoreState {
  sessionId: string | null;
  filename: string | null;
  columns: string[];
  rowCount: number;
  isLoading: boolean;
  currentModule: string;
  edaResults: any | null;
  setEdaResults: (data: any) => void;
  cleaningResults: any | null;
  setCleaningResults: (data: any) => void;
  mlResults: any | null;
  setMlResults: (data: any) => void;
  insightsResults: any | null;
  setInsightsResults: (data: any) => void;
  nlHistory: any[];
  setNlHistory: (data: any[]) => void;
  biHtmlResult: string | null;
  setBiHtmlResult: (html: string | null) => void;
  setSessionId: (id: string | null) => void;
  setFilename: (name: string | null) => void;
  setColumns: (cols: string[]) => void;
  setRowCount: (count: number) => void;
  setIsLoading: (loading: boolean) => void;
  setCurrentModule: (mod: string) => void;
}

const StoreContext = createContext<StoreState | undefined>(undefined);

export const StoreProvider = ({ children }: { children: ReactNode }) => {
  const [sessionId, setSessionId] = useState(null as string | null);
  const [filename, setFilename] = useState(null as string | null);
  const [columns, setColumns] = useState([] as string[]);
  const [rowCount, setRowCount] = useState(0);
  const [isLoading, setIsLoading] = useState(false);
  const [currentModule, setCurrentModule] = useState('dashboard');
  const [edaResults, setEdaResults] = useState(null as any | null);
  const [cleaningResults, setCleaningResults] = useState(null as any | null);
  const [mlResults, setMlResults] = useState(null as any | null);
  const [biHtmlResult, setBiHtmlResult] = useState<string | null>(null);
  const [insightsResults, setInsightsResults] = useState(null as any | null);
  const [nlHistory, setNlHistory] = useState([] as any[]);

  return (
    <StoreContext.Provider value={{
      sessionId,
      filename,
      columns,
      rowCount,
      isLoading,
      currentModule,
      edaResults,
      setEdaResults,
      cleaningResults,
      setCleaningResults,
      mlResults,
      setMlResults,
      insightsResults,
      setInsightsResults,
      nlHistory,
      biHtmlResult,
      setBiHtmlResult,
      setNlHistory,
      setSessionId,
      setFilename,
      setColumns,
      setRowCount,
      setIsLoading,
      setCurrentModule
    }}>
      {children}
    </StoreContext.Provider>
  );
};

export const useStore = () => {
  const context = useContext(StoreContext);
  if (context === undefined) {
    throw new Error('useStore must be used within a StoreProvider');
  }
  return context;
};
