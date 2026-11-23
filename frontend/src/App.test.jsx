import { render, screen, fireEvent, waitFor, cleanup } from "@testing-library/react";
import { test, expect, vi, afterEach } from "vitest";
import App from "./App";

vi.mock("./GoogleButton", () => ({ default: () => null }));
afterEach(() => {
  cleanup();
  vi.restoreAllMocks();
});

test("registers a learner from the login screen and signs them in", async () => {
  const fetchMock = vi.fn(async (url) => {
    if (url === "/auth/register") return { ok: true, json: async () => ({ id: 1, role: "admin" }) };
    if (url === "/auth/login") return { ok: true, json: async () => ({ token: "token", role: "admin", name: "Sam" }) };
    if (url === "/admin/dashboard") return { ok: true, json: async () => ({ courses: [], enrollments: [], stats: { enrollments: 0, certified: 0 } }) };
    return { ok: true, json: async () => [] };
  });
  vi.stubGlobal("fetch", fetchMock);
  render(<App />);

  fireEvent.click(screen.getByRole("button", { name: "Sign up" }));
  fireEvent.change(screen.getByPlaceholderText("Name"), { target: { value: "Sam" } });
  fireEvent.change(screen.getByPlaceholderText("Email"), { target: { value: "sam@example.com" } });
  fireEvent.change(screen.getByPlaceholderText("Password"), { target: { value: "secret1" } });
  fireEvent.click(screen.getByRole("button", { name: "Sign up" }));

  await waitFor(() => expect(screen.getByText("Sam")).toBeTruthy());
  expect(fetchMock.mock.calls[0][0]).toBe("/auth/register");
  expect(JSON.parse(fetchMock.mock.calls[0][1].body)).toEqual({
    name: "Sam",
    email: "sam@example.com",
    password: "secret1",
  });
  expect(fetchMock.mock.calls[1][0]).toBe("/auth/login");
});
