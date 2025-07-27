"use client";

import React, { createContext, useState, useContext, ReactNode, useEffect } from 'react';
import { useRouter, usePathname } from 'next/navigation';
import { auth, db } from '@/lib/firebase';
import { onAuthStateChanged, signInWithEmailAndPassword, createUserWithEmailAndPassword, signOut, User as FirebaseUser } from 'firebase/auth';
import { doc, setDoc, getDoc, Timestamp, GeoPoint } from 'firebase/firestore';

interface UserProfile {
  uid: string;
  email: string | null;
  displayName: string | null;
  interests: string[];
  homeLocation: GeoPoint | null;
  workLocation: GeoPoint | null;
  createdAt: Timestamp;
  updatedAt: Timestamp;
}

interface AuthContextType {
  user: UserProfile | null;
  login: (email: string, password: string) => Promise<void>;
  signup: (email: string, password: string, displayName: string) => Promise<void>;
  logout: () => Promise<void>;
  loading: boolean;
}

const AuthContext = createContext<AuthContextType | undefined>(undefined);

export function AuthProvider({ children }: { children: ReactNode }) { 
  const [user, setUser] = useState<UserProfile | null>(null);
  const [loading, setLoading] = useState(true); // Set initial loading to true
  const router = useRouter();
  const pathname = usePathname();

  useEffect(() => {
    const unsubscribe = onAuthStateChanged(auth, async (firebaseUser) => {
      if (firebaseUser) {
        // User is signed in
        const userProfile = await getUserProfile(firebaseUser.uid);
        setUser(userProfile);
        if (pathname === '/login') {
          router.push('/');
        }
      } else {
        // User is signed out
        setUser(null);
        if (pathname !== '/login') {
          router.push('/login');
        }
      }
      setLoading(false);
    });

    return () => unsubscribe();
  }, [router, pathname]);

  const getUserProfile = async (uid: string) => {
    const docRef = doc(db, 'user-profile', uid);
    const docSnap = await getDoc(docRef);
    if (docSnap.exists()) {
      return docSnap.data() as UserProfile;
    } else {
      return null;
    }
  };

  const login = async (email: string, password: string) => {
    setLoading(true);
    try {
      await signInWithEmailAndPassword(auth, email, password);
      // onAuthStateChanged will handle setting the user and redirecting
    } catch (error) {
      console.error('Error logging in:', error);
      setLoading(false);
      throw error; // Re-throw for error handling in components
    } finally {
      setLoading(false);
    }
  };

  const signup = async (email: string, password: string, displayName: string) => {
    setLoading(true);
    try {
      const userCredential = await createUserWithEmailAndPassword(auth, email, password);
      const firebaseUser = userCredential.user;
      const newUserProfile: UserProfile = {
        uid: firebaseUser.uid,
        email: firebaseUser.email,
        displayName: displayName,
        interests: [], // Initialize with empty interests
        homeLocation: null, // Initialize with null
        workLocation: null, // Initialize with null
        createdAt: Timestamp.now(),
        updatedAt: Timestamp.now(),
      };
      // Create user profile in Firestore
      await setDoc(doc(db, 'user-profile', firebaseUser.uid), newUserProfile);
      // onAuthStateChanged will handle setting the user and redirecting
    } catch (error) {
      console.error('Error signing up:', error);
      setLoading(false);
      throw error; // Re-throw for error handling in components
    } finally {
      setLoading(false);
    }
  };

  const logout = async () => {
    setLoading(true);
    try {
      await signOut(auth);
      // onAuthStateChanged will handle setting the user and redirecting
    } catch (error) {
      console.error('Error logging out:', error);
      setLoading(false);
      throw error; // Re-throw for error handling in components
    } finally {
      setLoading(false);
    }
  };

  const value = { user, login, signup, logout, loading };

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth() {
  const context = useContext(AuthContext);
  if (context === undefined) {
    throw new Error('useAuth must be used within an AuthProvider');
  }
  return context;
}