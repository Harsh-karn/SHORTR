import { SignIn } from "@clerk/nextjs";

export default function Page() {
  return (
    <div className="flex min-h-screen items-center justify-center bg-muted/40">
      <SignIn />
    </div>
  );
}
