import { render, screen, fireEvent, cleanup } from "@testing-library/react";
import { test, expect, vi, afterEach } from "vitest";
import CourseList from "./CourseList";
afterEach(cleanup);
test("lists courses and starts one", () => {
  const onStart = vi.fn();
  render(<CourseList courses={[{ id: 7, title: "DSA Basics" }]} onStart={onStart} />);
  expect(screen.getByText(/DSA Basics/)).toBeTruthy();
  fireEvent.click(screen.getByText("Start")); expect(onStart).toHaveBeenCalledWith(7);
});
test("shows empty message", () => {
  render(<CourseList courses={[]} onStart={() => {}} />);
  expect(screen.getByText("No courses available yet.")).toBeTruthy();
});
test("filters by search text", () => {
  render(<CourseList courses={[{ id: 1, title: "DSA Basics", category: "Code" }, { id: 2, title: "Fire Safety", category: "Safety" }]} onStart={() => {}} />);
  fireEvent.change(screen.getByPlaceholderText("Search courses"), { target: { value: "fire" } });
  expect(screen.queryByText(/DSA Basics/)).toBeNull(); expect(screen.getByText(/Fire Safety/)).toBeTruthy();
});