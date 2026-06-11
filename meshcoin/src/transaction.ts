import { hash, sign, verify, shortId } from "./crypto";

export const GENESIS_SUPPLY = 1_000_000;
export const TX_TTL_MS = 24 * 60 * 60 * 1000; // 24h — txs olvidadas después

export interface Transaction {
  id: string;
  sender: string;       // public key hex
  receiver: string;     // public key hex
  amount: number;
  nonce: number;        // secuencial por sender — anti doble gasto
  timestamp: number;
  signature: string;
  witnesses: string[];  // public keys de nodos que confirmaron proximidad
  hops: number;         // saltos Bluetooth dados
}

export type UTXO = { txId: string; amount: number };

function txPayload(tx: Omit<Transaction, "id" | "signature" | "witnesses" | "hops">): string {
  return JSON.stringify({
    sender: tx.sender,
    receiver: tx.receiver,
    amount: tx.amount,
    nonce: tx.nonce,
    timestamp: tx.timestamp,
  });
}

export function createTransaction(
  sender: string,
  receiver: string,
  amount: number,
  nonce: number,
  privateKey: string
): Transaction {
  const timestamp = Date.now();
  const payload = txPayload({ sender, receiver, amount, nonce, timestamp });
  const signature = sign(payload, privateKey);
  const id = hash(payload + signature);

  return { id, sender, receiver, amount, nonce, timestamp, signature, witnesses: [], hops: 0 };
}

export function validateTransaction(tx: Transaction): { ok: boolean; reason?: string } {
  if (Date.now() - tx.timestamp > TX_TTL_MS) return { ok: false, reason: "expired" };
  if (tx.amount <= 0) return { ok: false, reason: "amount <= 0" };
  if (tx.sender === tx.receiver) return { ok: false, reason: "self-transfer" };

  const payload = txPayload(tx);
  if (!verify(payload, tx.signature, tx.sender)) return { ok: false, reason: "bad signature" };

  return { ok: true };
}

export function txSummary(tx: Transaction): string {
  return `TX[${tx.id.slice(0, 8)}] ${shortId(tx.sender)}→${shortId(tx.receiver)} ${tx.amount} coins nonce=${tx.nonce} hops=${tx.hops} witnesses=${tx.witnesses.length}`;
}
