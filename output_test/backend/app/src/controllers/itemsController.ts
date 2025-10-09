import { Request, Response } from 'express'
import * as repo from '../repository/inMemoryStore'

export const list = (_req: Request, res: Response) => {
  return res.json(repo.list())
}

export const create = (req: Request, res: Response) => {
  const { name } = req.body
  if (!name) return res.status(400).json({ error: 'name required' })
  const item = repo.add(name)
  return res.status(201).json(item)
}
