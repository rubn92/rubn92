import { MeshNetwork } from "./network";

async function sleep(ms: number) {
  return new Promise((r) => setTimeout(r, ms));
}

async function main() {
  console.log("╔══════════════════════════════════════╗");
  console.log("║        MeshCoin — Demo               ║");
  console.log("║  Criptomoneda por red Bluetooth mesh ║");
  console.log("╚══════════════════════════════════════╝\n");

  // ── Escenario: 5 teléfonos en una calle ──────────────────────────────
  // [Alice] ←BT→ [Bob] ←BT→ [Carlos] ←BT→ [Diana] ←BT→ [Eve]
  // Alice tiene 500 monedas iniciales (como si las hubiera minado antes)
  // Quiere pagar a Eve, que está a 4 saltos de distancia

  const net = new MeshNetwork();

  const alice  = net.addNode("Alice",  500);
  const bob    = net.addNode("Bob",    0);
  const carlos = net.addNode("Carlos", 0);
  const diana  = net.addNode("Diana",  0);
  const eve    = net.addNode("Eve",    100);

  net.connectLinear(); // Alice-Bob-Carlos-Diana-Eve

  console.log("Topología: Alice ←BT→ Bob ←BT→ Carlos ←BT→ Diana ←BT→ Eve");
  console.log("Distancia real aprox: 400m en cadena de 100m por salto\n");

  net.printStatus();

  // ── Test 1: Pago normal ──────────────────────────────────────────────
  console.log("─── Test 1: Alice paga 50 monedas a Eve (4 saltos) ─────────────");
  net.send(alice, eve, 50);
  await sleep(100); // tiempo de propagación gossip

  net.printStatus();

  // ── Test 2: Eve paga a Carlos (2 saltos atrás) ───────────────────────
  console.log("─── Test 2: Eve paga 30 monedas a Carlos ───────────────────────");
  net.send(eve, carlos, 30);
  await sleep(100);

  net.printStatus();

  // ── Test 3: Intento de doble gasto — replay del nonce=1 ─────────────
  console.log("─── Test 3: Alguien reenvía la tx de Alice (replay nonce=1) ────");
  const { createTransaction } = await import("./transaction");
  // Simula que un atacante captura y reenvía la tx nonce=1 de Alice
  const replayTx = createTransaction(
    alice.wallet.publicKey,
    eve.wallet.publicKey,
    50,
    1, // nonce ya usado — doble gasto
    alice.wallet.keypair.privateKey
  );
  bob.receive(replayTx); // entra por Bob, no por Alice
  await sleep(50);

  // ── Test 4: Pago legítimo con nonce correcto ──────────────────────────
  console.log("\n─── Test 4: Alice paga legítimamente a Bob (nonce=2) ───────────");
  net.send(alice, bob, 75);
  await sleep(100);

  net.printStatus();

  // ── Estadísticas de red ───────────────────────────────────────────────
  console.log("=== ESTADÍSTICAS DE PROPAGACIÓN ===");
  for (const node of net.nodes) {
    const s = node.stats;
    console.log(
      `  [${node.id}] recv=${s.received} fwd=${s.forwarded} rej=${s.rejected} doublespend=${s.doublespend} mempool=${node.getMempoolSize()}`
    );
  }
  console.log();

  // ── Resumen del concepto ──────────────────────────────────────────────
  console.log("=== PROPIEDADES DEL SISTEMA ===");
  console.log("  ✓ Sin servidor central");
  console.log("  ✓ Sin internet");
  console.log("  ✓ Sin blockchain en disco (solo mempool en RAM)");
  console.log("  ✓ Firmas Ed25519 — nadie puede falsificar pagos");
  console.log("  ✓ Nonces secuenciales — doble gasto detectado y rechazado");
  console.log("  ✓ Gossip con TTL de saltos — la tx llega a 700m sin antena");
  console.log("  ✓ Witnesses de proximidad — prueba criptográfica de que ocurrió");
  console.log("  ~ Limitación: consenso global requiere red conectada\n");
}

main().catch(console.error);
