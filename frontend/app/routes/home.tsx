import type { Route } from "./types/home";
import { Welcome } from "../welcome/welcome";

export function meta({}: Route.MetaArgs) {
  return [
    { title: "New React Router App" },
    { name: "description", content: "Welcome to React Router!" },
  ];
}

export default function Home() {
  return (
    <>
      <div className="flex flex-col items-center mt-10">
        <div className="flex tracking-wider items-center">
          <img src="/logo_memary.png" alt="Logo" />
          <h1 className="text-black font-bold text-3xl">emary</h1>
      </div>
      <h2 className="mt-5 text-3xl">
        Hi, User.
      </h2>
      <h3 className="mt-2 text-xl">Remember your life.</h3>
      </div>
    </>
  );
}
