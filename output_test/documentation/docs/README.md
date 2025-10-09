
# AutoDevOS – Generated Project Documentation

This project was generated from the prompt:

> Build a task tracker with create and list tasks

## Structure

- output/frontend/app: React + TypeScript app (Vite + Tailwind + Jest)
- output/backend/app: Node.js + Express + TypeScript API (Jest)
- agents/testing_agent/python: PyTest integration tests

## Running locally

- Frontend: npm install && npm run dev (in output/frontend/app)
- Backend: npm install && npm run dev (in output/backend/app)

## API

- GET /api/health -> { status: 'ok' }
- GET /api/items -> []
- POST /api/items { name } -> created item
