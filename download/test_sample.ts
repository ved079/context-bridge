/**
 * taskQueue.ts
 * ------------
 * A TypeScript priority task queue using a binary heap.
 * Sync version — no async/await, just pure heap operations.
 */

interface Task<T = unknown> {
  priority: number;
  id: string;
  execute: () => T;
}

class PriorityQueue<T = unknown> {
  private heap: Task<T>[] = [];

  enqueue(priority: number, id: string, execute: () => T): void {
    const task: Task<T> = { priority, id, execute };
    this.heap.push(task);
    this.bubbleUp(this.heap.length - 1);
  }

  dequeue(): Task<T> | undefined {
    if (this.heap.length === 0) return undefined;
    const root = this.heap[0];
    const last = this.heap.pop()!;
    if (this.heap.length > 0) {
      this.heap[0] = last;
      this.sinkDown(0);
    }
    return root;
  }

  peek(): Task<T> | undefined {
    return this.heap[0];
  }

  get size(): number {
    return this.heap.length;
  }

  private bubbleUp(i: number): void {
    while (i > 0) {
      const parent = Math.floor((i - 1) / 2);
      if (this.heap[i].priority >= this.heap[parent].priority) break;
      [this.heap[i], this.heap[parent]] = [this.heap[parent], this.heap[i]];
      i = parent;
    }
  }

  private sinkDown(i: number): void {
    const n = this.heap.length;
    while (true) {
      let smallest = i;
      const left = 2 * i + 1;
      const right = 2 * i + 2;
      if (left < n && this.heap[left].priority < this.heap[smallest].priority) smallest = left;
      if (right < n && this.heap[right].priority < this.heap[smallest].priority) smallest = right;
      if (smallest === i) break;
      [this.heap[i], this.heap[smallest]] = [this.heap[smallest], this.heap[i]];
      i = smallest;
    }
  }
}

// -- Demo --
const queue = new PriorityQueue<string>();
queue.enqueue(3, "low", () => "low priority done");
queue.enqueue(1, "high", () => "high priority done");
queue.enqueue(2, "medium", () => "medium priority done");

while (queue.size > 0) {
  const task = queue.dequeue()!;
  console.log(`[${task.id}] ${task.execute()}`);
}
