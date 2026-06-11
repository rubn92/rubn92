import { generateKeyPair, KeyPair, shortId } from "./crypto";
import { Transaction, UTXO } from "./transaction";

export class Wallet {
  readonly keypair: KeyPair;
  readonly name: string;

  // Estado local: solo mis monedas + nonce
  private balance: number;
  private nonce: number = 0;

  // Nonces conocidos de otros senders (para validar secuencia)
  readonly knownNonces = new Map<string, number>();

  constructor(name: string, initialBalance = 0) {
    this.keypair = generateKeyPair();
    this.name = name;
    this.balance = initialBalance;
  }

  get publicKey(): string {
    return this.keypair.publicKey;
  }

  get id(): string {
    return shortId(this.keypair.publicKey);
  }

  getBalance(): number {
    return this.balance;
  }

  nextNonce(): number {
    return ++this.nonce;
  }

  applyTransaction(tx: Transaction): void {
    if (tx.receiver === this.keypair.publicKey) {
      this.balance += tx.amount;
    }
    if (tx.sender === this.keypair.publicKey) {
      this.balance -= tx.amount;
    }
    // Actualiza nonce conocido del sender
    const prev = this.knownNonces.get(tx.sender) ?? 0;
    if (tx.nonce > prev) this.knownNonces.set(tx.sender, tx.nonce);
  }

  toString(): string {
    return `Wallet[${this.name}/${this.id}] balance=${this.balance}`;
  }
}
