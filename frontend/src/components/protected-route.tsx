import { Navigate } from 'react-router-dom';
import { useCookies } from 'react-cookie';
import { JSX, useEffect, useState } from 'react';

export default function ProtectedRoute({ children }: { children: JSX.Element }) {
  const [cookies] = useCookies(['authToken']);
  const [isValid, setIsValid] = useState(false);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const verifyToken = async () => {
      try {
        const response = await fetch('http://localhost:5000/api/verify-auth', {
          credentials: 'include'
        });
        
        if (response.ok) {
          const data = await response.json();
          setIsValid(data.role === 'hr');
        }
      } catch (error) {
        console.error('Auth verification error:', error);
      } finally {
        setLoading(false);
      }
    };

    verifyToken();
  }, []);

  if (loading) return <div>Loading...</div>;
  return isValid ? children : <Navigate to="/" replace />;
}