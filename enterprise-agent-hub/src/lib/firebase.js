import { initializeApp } from "firebase/app";
import { getAuth, GoogleAuthProvider } from "firebase/auth";

// 🔴 TODO: Replace these placeholders with your actual Firebase Project keys
// You can find these in your Firebase Console -> Project Settings -> General -> "Your apps"
const firebaseConfig = {
  apiKey: "AIzaSyCvmd9W5zdt6mEMOgqEnJxwtqzRuM7mNWY",
  authDomain: "aiintensiveproject.firebaseapp.com",
  projectId: "aiintensiveproject",
  storageBucket: "aiintensiveproject.firebasestorage.app",
  messagingSenderId: "484181815030",
  appId: "1:484181815030:web:8272877ff669dbb0c6c6d7",
  measurementId: "G-TCJZ3YZQLK"
};

const app = initializeApp(firebaseConfig);
export const auth = getAuth(app);

export const googleProvider = new GoogleAuthProvider();

// 🔴 ADD THIS: Ask for Drive & Docs permissions during Login
googleProvider.addScope('https://www.googleapis.com/auth/drive.file'); 
googleProvider.addScope('https://www.googleapis.com/auth/documents');
googleProvider.addScope('https://www.googleapis.com/auth/spreadsheets');

