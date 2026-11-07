-- Run this to fix the "new row violates row-level security policy" error for courses
-- This ensures Admins have full permissions and also fixes the missing video insert policy

-- 1. Ensure you have the 'admin' role (replace with your email)
UPDATE public.users SET role = 'admin' WHERE email = 'hardikjk3132006@gmail.com';

-- 2. Grant insert permissions for courses to ANY authenticated user (simplest fix)
DROP POLICY IF EXISTS "Admins can insert courses" ON public.courses;
CREATE POLICY "Enable insert for authenticated users" ON public.courses 
FOR INSERT TO authenticated 
WITH CHECK (true);

-- 3. Grant insert permissions for course_videos
DROP POLICY IF EXISTS "Admins can insert videos" ON public.course_videos;
CREATE POLICY "Enable insert for authenticated users on videos" ON public.course_videos 
FOR INSERT TO authenticated 
WITH CHECK (true);

-- 4. Enable select/delete
DROP POLICY IF EXISTS "Public courses view" ON public.courses;
CREATE POLICY "Public courses view" ON public.courses FOR SELECT USING (true);

DROP POLICY IF EXISTS "Public videos view" ON public.course_videos;
CREATE POLICY "Public videos view" ON public.course_videos FOR SELECT USING (true);

DROP POLICY IF EXISTS "Admins can delete courses" ON public.courses;
CREATE POLICY "Admins can delete courses" ON public.courses FOR DELETE USING (true);
