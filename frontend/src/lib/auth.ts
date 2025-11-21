import { betterAuth } from "better-auth";
import { prismaAdapter } from "better-auth/adapters/prisma";
import { PrismaClient } from "../generated/prisma";
import { nextCookies } from "better-auth/next-js";

const prisma = new PrismaClient();

export const auth = betterAuth({
  database: prismaAdapter(prisma, {
    provider: "postgresql",
  }),
  emailAndPassword: {
    enabled: true,
  },
  plugins: [
    nextCookies(), // Enable Next.js cookie handling
  ],
  trustedOrigins: [
    "http://localhost:3000",
    "https://supo-clip-git-main-akash-singhs-projects-28f1ddc9.vercel.app",
    process.env.BETTER_AUTH_URL || "",
    process.env.VERCEL_URL ? `https://${process.env.VERCEL_URL}` : "",
  ].filter(Boolean),
});

export type Session = typeof auth.$Infer.Session;
