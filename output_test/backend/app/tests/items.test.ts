import request from 'supertest'
import app from '../src/app'

describe('items api', () => {
  it('lists empty initially', async () => {
    const res = await request(app).get('/api/items')
    expect(res.status).toBe(200)
    expect(res.body).toEqual([])
  })

  it('creates an item', async () => {
    const res = await request(app).post('/api/items').send({ name: 'Sample' })
    expect(res.status).toBe(201)
    expect(res.body.name).toBe('Sample')
  })
})
