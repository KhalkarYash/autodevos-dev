import express from 'express'
import cors from 'cors'
import itemsRouter from './routes/items'

const app = express()
app.use(cors())
app.use(express.json())
app.get('/api/health', (_req, res) => res.json({ status: 'ok' }))
app.use('/api/items', itemsRouter)

export default app
