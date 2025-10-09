import { Item } from '../models/item'
const store: Item[] = []
export const list = () => store
export const add = (name: string): Item => {
  const item: Item = { id: String(Date.now()), name }
  store.push(item)
  return item
}
