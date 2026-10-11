import { render, screen, fireEvent, waitFor, cleanup } from "@testing-library/react";
import { test, expect, vi, afterEach } from "vitest";
import QuizView from "./QuizView";
afterEach(cleanup);
const qs = [{ id: 1, text: "2+2?", options: ["3", "4"] }];
test("shows score and per-question feedback after submit", async () => {
  const onSubmit = vi.fn().mockResolvedValue({ score: 100, passed: true, results: [{ question_id: 1, correct: true }] });
  render(<QuizView questions={qs} onSubmit={onSubmit} />);
  fireEvent.click(screen.getByLabelText("4")); fireEvent.click(screen.getByText("Submit"));
  await waitFor(() => expect(screen.getByText(/Passed!/)).toBeTruthy());
  expect(onSubmit).toHaveBeenCalledWith({ 1: 1 }); expect(screen.getByText("✓ Correct")).toBeTruthy();
});
test("shows error on failure", async () => {
  render(<QuizView questions={qs} onSubmit={() => Promise.reject(new Error())} />);
  fireEvent.click(screen.getByText("Submit"));
  await waitFor(() => expect(screen.getByRole("alert")).toBeTruthy());
});