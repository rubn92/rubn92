import { createHash, createSign, createVerify, generateKeyPairSync } from "crypto";

export interface KeyPair {
  publicKey: string;
  privateKey: string;
}

export function generateKeyPair(): KeyPair {
  const { publicKey, privateKey } = generateKeyPairSync("ed25519", {
    publicKeyEncoding: { type: "spki", format: "der" },
    privateKeyEncoding: { type: "pkcs8", format: "der" },
  });
  return {
    publicKey: publicKey.toString("hex"),
    privateKey: privateKey.toString("hex"),
  };
}

export function sign(data: string, privateKeyHex: string): string {
  const privateKey = Buffer.from(privateKeyHex, "hex");
  const sign = createSign("SHA256");
  sign.update(data);
  // Ed25519 doesn't use SHA256 digest separately, use raw sign
  const keyObj = require("crypto").createPrivateKey({
    key: privateKey,
    format: "der",
    type: "pkcs8",
  });
  return require("crypto").sign(null, Buffer.from(data), keyObj).toString("hex");
}

export function verify(data: string, signature: string, publicKeyHex: string): boolean {
  try {
    const publicKey = Buffer.from(publicKeyHex, "hex");
    const keyObj = require("crypto").createPublicKey({
      key: publicKey,
      format: "der",
      type: "spki",
    });
    return require("crypto").verify(
      null,
      Buffer.from(data),
      keyObj,
      Buffer.from(signature, "hex")
    );
  } catch {
    return false;
  }
}

export function hash(data: string): string {
  return createHash("sha256").update(data).digest("hex");
}

export function shortId(publicKey: string): string {
  return hash(publicKey).slice(0, 8);
}
