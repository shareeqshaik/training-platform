-- PostgreSQL schema for the Training Platform (the app also creates these tables automatically on startup)
CREATE TABLE users (
  id SERIAL PRIMARY KEY,
  email TEXT UNIQUE NOT NULL,
  name TEXT NOT NULL,
  pw TEXT NOT NULL,
  role TEXT NOT NULL DEFAULT 'user' CHECK (role IN ('admin', 'user'))
);
CREATE TABLE courses (
  id SERIAL PRIMARY KEY,
  title TEXT NOT NULL,
  description TEXT DEFAULT '',
  category TEXT DEFAULT ''
);
CREATE TABLE modules (
  id SERIAL PRIMARY KEY,
  course_id INT NOT NULL REFERENCES courses ON DELETE CASCADE,
  position INT NOT NULL,
  title TEXT NOT NULL,
  content TEXT DEFAULT '',
  video_url TEXT
);
CREATE TABLE quizzes (
  id SERIAL PRIMARY KEY,
  module_id INT UNIQUE NOT NULL REFERENCES modules ON DELETE CASCADE,
  passing_score INT NOT NULL CHECK (passing_score BETWEEN 1 AND 100),
  max_attempts INT
);
CREATE TABLE questions (
  id SERIAL PRIMARY KEY,
  quiz_id INT NOT NULL REFERENCES quizzes ON DELETE CASCADE,
  text TEXT NOT NULL,
  options JSON NOT NULL,
  correct INT NOT NULL
);
CREATE TABLE enrollments (
  id SERIAL PRIMARY KEY,
  user_id INT NOT NULL REFERENCES users ON DELETE CASCADE,
  course_id INT NOT NULL REFERENCES courses ON DELETE CASCADE,
  created TIMESTAMP DEFAULT now(),
  due_date DATE,
  UNIQUE (user_id, course_id)
);
CREATE TABLE attempts (
  id SERIAL PRIMARY KEY,
  enrollment_id INT NOT NULL REFERENCES enrollments ON DELETE CASCADE,
  module_id INT NOT NULL REFERENCES modules ON DELETE CASCADE,
  score INT NOT NULL,
  passed BOOLEAN NOT NULL,
  created TIMESTAMP DEFAULT now()
);
CREATE TABLE certificates (
  id SERIAL PRIMARY KEY,
  enrollment_id INT UNIQUE NOT NULL REFERENCES enrollments ON DELETE CASCADE,
  number TEXT UNIQUE NOT NULL,
  score INT NOT NULL,
  issued TIMESTAMP DEFAULT now()
);