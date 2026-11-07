-- 1. Create Users table (extends Supabase Auth)
CREATE TABLE public.users (
    id UUID REFERENCES auth.users NOT NULL PRIMARY KEY,
    email TEXT,
    role TEXT DEFAULT 'user',
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- 2. Create Courses table
CREATE TABLE public.courses (
    id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    title TEXT NOT NULL,
    description TEXT,
    created_by UUID REFERENCES public.users(id),
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- 3. Create Course Videos table
CREATE TABLE public.course_videos (
    id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    course_id UUID REFERENCES public.courses(id) ON DELETE CASCADE,
    youtube_url TEXT NOT NULL,
    youtube_video_id TEXT NOT NULL,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- 4. Create Emotion Logs table
CREATE TABLE public.emotion_logs (
    id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    user_id UUID REFERENCES public.users(id) ON DELETE CASCADE,
    course_id UUID REFERENCES public.courses(id) ON DELETE CASCADE,
    emotion TEXT NOT NULL,
    confidence_score FLOAT NOT NULL,
    video_timestamp TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Enable Row Level Security (RLS)
ALTER TABLE public.users ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.courses ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.course_videos ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.emotion_logs ENABLE ROW LEVEL SECURITY;

-- 5. Define Policies
-- Users can read profiles (needed for role checks during login)
CREATE POLICY "Enable read for all authenticated users" ON public.users FOR SELECT TO authenticated USING (true);
-- Users can insert their own profile
CREATE POLICY "Enable insert for authenticated users" ON public.users FOR INSERT TO authenticated WITH CHECK (auth.uid() = id);
-- Users can update their own data
CREATE POLICY "Enable update for users based on id" ON public.users FOR UPDATE TO authenticated USING (auth.uid() = id);

-- 5. Trigger for New User Creation
-- This function automatically creates a record in public.users when a user signs up via Auth
CREATE OR REPLACE FUNCTION public.handle_new_user()
RETURNS TRIGGER 
LANGUAGE plpgsql 
SECURITY DEFINER SET search_path = public
AS $$
BEGIN
  INSERT INTO public.users (id, email, role)
  VALUES (NEW.id, NEW.email, 'user')
  ON CONFLICT (id) DO NOTHING;
  RETURN NEW;
END;
$$;

-- Trigger to fire after a new user is created in auth.users
CREATE OR REPLACE TRIGGER on_auth_user_created
  AFTER INSERT ON auth.users
  FOR EACH ROW EXECUTE PROCEDURE public.handle_new_user();

-- Everyone can view courses and videos
CREATE POLICY "Public courses view" ON public.courses FOR SELECT USING (true);
CREATE POLICY "Public videos view" ON public.course_videos FOR SELECT USING (true);

-- Admins can do everything (Example for courses)
-- Note: Replace with proper role-based check if using a different method
CREATE POLICY "Admins can insert courses" ON public.courses FOR INSERT WITH CHECK (
  EXISTS (SELECT 1 FROM public.users WHERE id = auth.uid() AND role = 'admin')
);

-- 6. DUMMY DATA (Optional)
-- Insert a dummy course (Requirement: A user must exist first for created_by, or remove the foreign key check temporarily)
-- For demonstration, you can comment out the created_by constraint or run this after signing up.

/*
INSERT INTO public.courses (title, description) VALUES 
('Introduction to Emotional Intelligence', 'Learn how to recognize and manage your own emotions and those of others.'),
('The Science of Happiness', 'Explore psychological and biological factors that contribute to human well-being.');
*/

-- 7. HOW TO CREATE AN ADMIN
-- Step 1: Sign up via the application UI.
-- Step 2: Run the following SQL in the Supabase SQL Editor (replace with your email):

-- UPDATE public.users SET role = 'admin' WHERE email = 'your-email@example.com';
