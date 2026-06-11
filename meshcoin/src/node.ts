import { Wallet } from "./wallet";
import { Transaction, validateTransaction, txSummary } from "./transaction";
import { sign, shortId } from "./crypto";

const MAX_HOPS = 7;        // máximo saltos Bluetooth (~700m en chain de 100m)
const MEMPOOL_MAX = 500;   // txs máximas en memoria

export class MeshNode {
  readonly wallet: Wallet;
  readonly peers = new Set<MeshNode>();

  // Mempool: txs válidas vistas — sin blockchain, sin disco
  private mempool = new Map<string, Transaction>();

  // Índice nonce: sender → último nonce aceptado
  private nonceIndex = new Map<string, number>();

  // Métrica de red
  stats = { received: 0, forwarded: 0, rejected: 0, doublespend: 0 };

  constructor(wallet: Wallet) {
    this.wallet = wallet;
  }

  get id(): string {
    return this.wallet.id;
  }

  // Simula conexión Bluetooth con otro nodo próximo
  connect(other: MeshNode): void {
    this.peers.add(other);
    other.peers.add(this);
  }

  // Recibe una transacción (puede venir del usuario local o de un peer)
  receive(tx: Transaction, fromPeer?: string): void {
    this.stats.received++;

    // Ya la vimos
    if (this.mempool.has(tx.id)) return;

    // Validación criptográfica
    const { ok, reason } = validateTransaction(tx);
    if (!ok) {
      this.stats.rejected++;
      this.log(`REJECT [${reason}] ${txSummary(tx)}`);
      return;
    }

    // Anti doble-gasto: nonce secuencial
    const lastNonce = this.nonceIndex.get(tx.sender) ?? 0;
    if (tx.nonce !== lastNonce + 1) {
      this.stats.doublespend++;
      this.log(`DOUBLE-SPEND nonce=${tx.nonce} expected=${lastNonce + 1} ${txSummary(tx)}`);
      return;
    }

    // Soy testigo de proximidad (witness) — firmo que vi esta tx
    const txWithWitness = this.addWitness(tx);

    // Aplico al wallet local si me afecta
    this.wallet.applyTransaction(txWithWitness);

    // Guardo en mempool
    this.nonceIndex.set(tx.sender, tx.nonce);
    this.mempool.set(txWithWitness.id, txWithWitness);
    this.log(`ACCEPT ${txSummary(txWithWitness)}`);

    // Gestión de tamaño
    if (this.mempool.size > MEMPOOL_MAX) this.evictOldest();

    // Propago a peers (gossip) si no superó max hops
    if (txWithWitness.hops < MAX_HOPS) {
      this.gossip(txWithWitness, fromPeer);
    }
  }

  // Agrego mi firma como witness de proximidad
  private addWitness(tx: Transaction): Transaction {
    const updated: Transaction = {
      ...tx,
      hops: tx.hops + 1,
      witnesses: [...tx.witnesses, this.wallet.publicKey],
    };
    return updated;
  }

  // Propaga a todos los peers excepto de donde vino
  private gossip(tx: Transaction, exceptPeer?: string): void {
    for (const peer of this.peers) {
      if (peer.id === exceptPeer) continue;
      this.stats.forwarded++;
      // Simula latencia Bluetooth (~10ms)
      setImmediate(() => peer.receive(tx, this.id));
    }
  }

  private evictOldest(): void {
    const oldest = [...this.mempool.values()].sort((a, b) => a.timestamp - b.timestamp)[0];
    if (oldest) this.mempool.delete(oldest.id);
  }

  getMempoolSize(): number {
    return this.mempool.size;
  }

  getTransaction(id: string): Transaction | undefined {
    return this.mempool.get(id);
  }

  private log(msg: string): void {
    console.log(`[Node ${this.id}] ${msg}`);
  }

  toString(): string {
    return `Node[${this.id}] peers=${this.peers.size} mempool=${this.mempool.size} balance=${this.wallet.getBalance()}`;
  }
}
