import { MeshNode } from "./node";
import { Wallet } from "./wallet";
import { createTransaction } from "./transaction";

export class MeshNetwork {
  readonly nodes: MeshNode[] = [];

  addNode(name: string, initialBalance = 0): MeshNode {
    const wallet = new Wallet(name, initialBalance);
    const node = new MeshNode(wallet);
    this.nodes.push(node);
    return node;
  }

  // Topología lineal: A-B-C-D (como un pasillo de tiendas)
  connectLinear(): void {
    for (let i = 0; i < this.nodes.length - 1; i++) {
      this.nodes[i].connect(this.nodes[i + 1]);
    }
  }

  // Topología random: cada nodo conecta con ~3 vecinos aleatorios
  connectRandom(avgPeers = 3): void {
    for (const node of this.nodes) {
      const candidates = this.nodes.filter((n) => n !== node && !node.peers.has(n));
      const k = Math.min(avgPeers, candidates.length);
      for (let i = 0; i < k; i++) {
        const idx = Math.floor(Math.random() * candidates.length);
        node.connect(candidates.splice(idx, 1)[0]);
      }
    }
  }

  send(from: MeshNode, to: MeshNode, amount: number): void {
    const nonce = from.wallet.nextNonce();
    const tx = createTransaction(
      from.wallet.publicKey,
      to.wallet.publicKey,
      amount,
      nonce,
      from.wallet.keypair.privateKey
    );
    console.log(`\n→ SENDING ${from.wallet.name} → ${to.wallet.name}: ${amount} coins`);
    from.receive(tx);
  }

  printStatus(): void {
    console.log("\n=== ESTADO DE LA RED MESH ===");
    for (const node of this.nodes) {
      console.log(`  ${node.toString()}`);
    }
    console.log("");
  }
}
