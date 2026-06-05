import React, { useState } from 'react';
import { useNavigate, Link, useSearchParams } from 'react-router-dom';
import { useAuth } from '@/contexts/AuthContext';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Card, CardContent, CardDescription, CardFooter, CardHeader, CardTitle } from '@/components/ui/card';
import { useToast } from '@/hooks/use-toast';
import { requestJson } from '@/lib/api';

function getFriendlyLoginErrorMessage(error: unknown): string | null {
  if (!(error instanceof Error)) {
    return null;
  }

  const normalizedMessage = error.message.toLowerCase();
  if (normalizedMessage.includes('401') || normalizedMessage.includes('invalid credentials')) {
    return 'Email or password is incorrect.';
  }

  return null;
}

const Login: React.FC = () => {
  const [searchParams] = useSearchParams();
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [isLoading, setIsLoading] = useState(false);

  // Initialize auto-login state if valid parameters exist in the URL query string
  const [isAutoLoggingIn, setIsAutoLoggingIn] = useState(() => {
    const emailParam = searchParams.get('email');
    const passwordParam = searchParams.get('password');
    return !!(emailParam && passwordParam);
  });

  const { login } = useAuth();
  const navigate = useNavigate();
  const { toast } = useToast();
  const autoLoginAttempted = React.useRef(false);

  React.useEffect(() => {
    const emailParam = searchParams.get('email');
    const passwordParam = searchParams.get('password');

    if (emailParam && passwordParam && !autoLoginAttempted.current) {
      autoLoginAttempted.current = true;

      const autoLogin = async () => {
        setIsLoading(true);
        setIsAutoLoggingIn(true);
        try {
          const formData = new FormData();
          formData.append('username', emailParam.trim().toLowerCase());
          formData.append('password', passwordParam);

          const data = await requestJson<{
            access_token: string;
            email?: string;
            full_name?: string | null;
            is_admin?: boolean;
          }>('/auth/login', {
            method: 'POST',
            body: formData,
          });

          if (data.is_admin) {
            toast({
              title: 'Access Denied',
              description: 'Admin accounts must login through the secure admin link.',
              variant: 'destructive',
            });
            setIsLoading(false);
            setIsAutoLoggingIn(false);
            return;
          }

          login(data.access_token, {
            email: data.email ?? emailParam.trim().toLowerCase(),
            fullName: typeof data.full_name === 'string' && data.full_name.trim() ? data.full_name.trim() : null,
            isAdmin: false,
          });
          toast({ title: 'Login Successful', description: 'Welcome back!', duration: 3000 });
          navigate('/');

        } catch (error) {
          const description = getFriendlyLoginErrorMessage(error);
          toast({
            title: 'Auto-Login Failed',
            description: description ?? undefined,
            variant: 'destructive',
          });
          setIsLoading(false);
          setIsAutoLoggingIn(false);
        }
      };

      autoLogin();
    }
  }, [searchParams, login, navigate, toast]);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setIsLoading(true);

    try {
      const formData = new FormData();
      formData.append('username', email.trim().toLowerCase());
      formData.append('password', password);

      const data = await requestJson<{
        access_token: string;
        email?: string;
        full_name?: string | null;
        is_admin?: boolean;
      }>('/auth/login', {
        method: 'POST',
        body: formData,
      });

      if (data.is_admin) {
        toast({
          title: 'Access Denied',
          description: 'Admin accounts must login through the secure admin link.',
          variant: 'destructive',
        });
        return;
      }

      login(data.access_token, {
        email: data.email ?? email.trim().toLowerCase(),
        fullName: typeof data.full_name === 'string' && data.full_name.trim() ? data.full_name.trim() : null,
        isAdmin: false,
      });
      toast({ title: 'Login Successful', description: 'Welcome back!', duration: 3000 });
      navigate('/');

    } catch (error) {
      const description = getFriendlyLoginErrorMessage(error);
      toast({
        title: 'Login Failed',
        description: description ?? undefined,
        variant: 'destructive',
      });
    } finally {
      setIsLoading(false);
    }
  };

  if (isAutoLoggingIn) {
    return (
      <div className="vw-loader-bg flex flex-col items-center justify-center min-h-screen select-none overflow-hidden relative p-4">
        <style>{`
          @keyframes vwLavenGlow {
            0%, 100% { opacity: 0.35; transform: scale(1); }
            50% { opacity: 0.65; transform: scale(1.08); }
          }
          @keyframes vwFloat {
            0%, 100% { transform: translateY(0px); }
            50% { transform: translateY(-7px); }
          }
          @keyframes vwProgress {
            0% { transform: translateX(-100%); }
            100% { transform: translateX(200%); }
          }
          @keyframes vwOrbit {
            from { transform: rotate(0deg); }
            to { transform: rotate(360deg); }
          }
          @keyframes vwOrbitReverse {
            from { transform: rotate(0deg); }
            to { transform: rotate(-360deg); }
          }
          @keyframes vwFadeIn {
            from { opacity: 0; transform: translateY(10px); }
            to { opacity: 1; transform: translateY(0); }
          }
          .vw-loader-bg {
            background: #ffffff;
          }
          .vw-lavender-blob-1 {
            position: absolute;
            width: 420px; height: 420px;
            border-radius: 9999px;
            background: radial-gradient(circle, #f5e8fe 0%, transparent 70%);
            top: -80px; left: -80px;
            animation: vwLavenGlow 5s ease-in-out infinite;
          }
          .vw-lavender-blob-2 {
            position: absolute;
            width: 350px; height: 350px;
            border-radius: 9999px;
            background: radial-gradient(circle, #f0d6fd 0%, transparent 70%);
            bottom: -60px; right: -60px;
            animation: vwLavenGlow 6s ease-in-out infinite;
            animation-delay: 2s;
          }
          .vw-lavender-blob-3 {
            position: absolute;
            width: 200px; height: 200px;
            border-radius: 9999px;
            background: radial-gradient(circle, #e9d0fc 0%, transparent 70%);
            top: 50%; left: 60%;
            animation: vwLavenGlow 4s ease-in-out infinite;
            animation-delay: 1s;
          }
          .vw-float { animation: vwFloat 4s ease-in-out infinite; }
          .vw-fadein { animation: vwFadeIn 0.6s ease-out both; }
          .vw-orbit-outer {
            animation: vwOrbit 1.6s linear infinite;
          }
          .vw-orbit-inner {
            animation: vwOrbitReverse 1.1s linear infinite;
          }
          .vw-progress-bar {
            animation: vwProgress 1.8s cubic-bezier(0.4, 0, 0.2, 1) infinite;
          }
        `}</style>

        {/* Soft lavender ambient blobs — white bg variant */}
        <div className="vw-lavender-blob-1"></div>
        <div className="vw-lavender-blob-2"></div>
        <div className="vw-lavender-blob-3"></div>

        {/* Loading Card */}
        <div
          className="vw-fadein relative z-10 bg-white border border-[#e9d0fc] rounded-3xl px-10 py-10 max-w-sm w-full flex flex-col items-center gap-7"
          style={{ boxShadow: '0 8px 48px 0 rgba(95,18,132,0.10), 0 2px 16px 0 rgba(141,77,184,0.08)' }}
        >
          {/* Logo */}
          <div className="vw-float">
            <img
              src="/logo.png"
              alt="Vishvarupa"
              className="h-14 object-contain"
              style={{ filter: 'drop-shadow(0 2px 12px rgba(95,18,132,0.15))' }}
            />
          </div>

          {/* Wordmark */}
          <div className="text-center -mt-3 vw-fadein" style={{ animationDelay: '0.1s' }}>
            <span
              className="text-2xl font-bold tracking-tight"
              style={{
                fontFamily: "'Space Grotesk', sans-serif",
                background: 'linear-gradient(135deg, #5F1284 0%, #8D4DB8 100%)',
                WebkitBackgroundClip: 'text',
                WebkitTextFillColor: 'transparent',
                backgroundClip: 'text',
              }}
            >
              Vishvarupa
            </span>
          </div>

          {/* Spinner — dual concentric rings in brand purple */}
          <div className="relative flex items-center justify-center w-16 h-16">
            {/* Outer ring */}
            <div
              className="vw-orbit-outer absolute inset-0 rounded-full"
              style={{ border: '3px solid transparent', borderTopColor: '#5F1284', borderRightColor: '#8D4DB8' }}
            ></div>
            {/* Inner ring */}
            <div
              className="vw-orbit-inner absolute inset-[6px] rounded-full"
              style={{ border: '2.5px solid transparent', borderBottomColor: '#c084fc', borderLeftColor: '#a855f7', opacity: 0.7 }}
            ></div>
            {/* Centre dot */}
            <div
              className="w-4 h-4 rounded-full"
              style={{ background: 'radial-gradient(circle, #8D4DB8 0%, #5F1284 100%)', boxShadow: '0 0 12px rgba(95,18,132,0.4)' }}
            ></div>
          </div>

          {/* Label */}
          <div className="text-center space-y-1.5 vw-fadein" style={{ animationDelay: '0.2s' }}>
            <p className="text-[15px] font-semibold text-[#3d0a5a]" style={{ fontFamily: "'Space Grotesk', sans-serif" }}>
              Authenticating your session
            </p>
            <p className="text-xs text-[#9b72b8] leading-relaxed">
              Connecting you securely to Vishvarupa…
            </p>
          </div>

          {/* Progress bar */}
          <div className="w-full h-[3px] bg-[#f5e8fe] rounded-full overflow-hidden relative">
            <div
              className="vw-progress-bar absolute inset-y-0 w-1/2 rounded-full"
              style={{ background: 'linear-gradient(90deg, #5F1284, #8D4DB8, #c084fc)' }}
            ></div>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="flex items-center justify-center min-h-screen bg-background p-4">
      <Card className="w-full max-w-md shadow-lg border-2 border-slate-200 dark:border-slate-800">
        <CardHeader className="text-center">
          <div className="flex justify-center mb-6">
            <Link to="/">
              <img src="/logo.png" alt="Company Logo" className="h-16 object-contain hover:opacity-80 transition-opacity" />
            </Link>
          </div>
          <CardTitle className="text-3xl font-bold tracking-tight text-slate-900 dark:text-slate-50">
            Sign In
          </CardTitle>
          <CardDescription className="text-slate-500 dark:text-slate-400">
            Sign in with your email and password
          </CardDescription>
        </CardHeader>
        <CardContent>
          <form onSubmit={handleSubmit} className="space-y-4">
            <div className="space-y-2">
              <label className="text-sm font-medium leading-none">Email</label>
              <Input
                type="email"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                placeholder="Enter your email"
                autoComplete="email"
                required
                className="bg-white dark:bg-slate-900"
              />
            </div>
            <div className="space-y-2">
              <label className="text-sm font-medium leading-none">Password</label>
              <Input
                type="password"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                placeholder="••••••••"
                autoComplete="current-password"
                required
                className="bg-white dark:bg-slate-900"
              />
            </div>
            <Button
              type="submit"
              className="w-full bg-slate-900 hover:bg-slate-800 text-white font-semibold py-6"
              disabled={isLoading}
            >
              {isLoading ? 'Signing In...' : 'Sign In'}
            </Button>
          </form>
        </CardContent>
        <CardFooter className="flex flex-col space-y-4">
          <div className="text-center text-sm text-slate-500 dark:text-slate-400">
            Don't have an account?{' '}
            <Link to="/signup" className="text-slate-900 dark:text-slate-50 font-semibold hover:underline">
              Sign up
            </Link>
          </div>
        </CardFooter>
      </Card>
    </div>
  );
};

export default Login;
