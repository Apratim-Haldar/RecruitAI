import type { SVGProps } from "react";
import { useNavigate } from "react-router";
import { useState } from "react";
import { useCookies } from "react-cookie";

type prop = {
  handleCancel: () => void;
};

export default function Auth({ handleCancel }: prop) {
  const navigate = useNavigate();

  const [isSignUp, setIsSignUp] = useState(false);
  const [cookiesds, setCookie] = useCookies(["authToken"]);

  const handleSubmit = async (e: React.FormEvent<HTMLFormElement>) => {
    e.preventDefault();
    const formData = new FormData(e.currentTarget);

    try {
      const endpoint = isSignUp ? "/api/signup" : "/api/login";
      const response = await fetch(`http://localhost:5000${endpoint}`, {
        // Changed port to 3000
        method: "POST",
        headers: { "Content-Type": "application/json" },
        credentials: "include",
        body: JSON.stringify({
          name: formData.get("name"),
          email: formData.get("email"),
          password: formData.get("password"),
          role: formData.get("role") || "candidate", // Default to candidate
          companyCode: formData.get("companyCode") || undefined,
        }),
      });

      if (!response.ok) throw new Error(await response.text());

      const data = await response.json();
      
      if (data.user.role === "hr") {
        console.log(data);
        navigate("/hr");
      }
    } catch (error) {
      console.error("Authentication failed:", error);
    }
  };

  return (
    <section className=" relative flex size-full max-h-full items-center justify-center bg-cover px-2 py-6 md:px-12 ">
      <div className="relative z-10 flex flex-1 flex-col rounded-3xl border-white/50 border-t bg-white/60 px-4 py-10 backdrop-blur-2xl sm:justify-center md:flex-none md:px-20 lg:border-t-0 lg:border-l lg:py-24">
        <div className="mx-auto w-full max-w-md sm:px-4 md:w-96 md:max-w-sm md:px-0">
          <h1 className="font-semibold text-3xl text-neutral-900 tracking-tighter">
            Get Started <span className="text-neutral-600">in seconds</span>
          </h1>
          <p className="mt-4 font-medium text-base text-neutral-500">
            Explore job opportunities at TechCorp
          </p>
          <div className="mt-8"></div>
          <form onSubmit={handleSubmit}>
            <div className="space-y-3">
              {isSignUp && (
                <div>
                  <label
                    className="mb-3 block font-medium text-black text-sm"
                    htmlFor="name"
                  >
                    Full Name
                  </label>
                  <input
                    className="block h-12 w-full appearance-none rounded-xl bg-white px-4 py-2 placeholder-neutral-300 duration-200 focus:outline-hidden focus:ring-neutral-300 sm:text-sm"
                    id="name"
                    name="name" // Added name attribute
                    placeholder="Your name"
                    type="text"
                    required
                  />
                </div>
              )}

              <div>
                <label
                  className="mb-3 block font-medium text-black text-sm"
                  htmlFor="email"
                >
                  Email
                </label>
                <input
                  className="block h-12 w-full appearance-none rounded-xl bg-white px-4 py-2 placeholder-neutral-300 duration-200 focus:outline-hidden focus:ring-neutral-300 sm:text-sm"
                  id="email"
                  name="email" // Added name attribute
                  placeholder="work@email.com"
                  type="email"
                  required
                />
              </div>

              <div>
                <label
                  className="mb-3 block font-medium text-black text-sm"
                  htmlFor="password"
                >
                  Password
                </label>
                <input
                  className="block h-12 w-full appearance-none rounded-xl bg-white px-4 py-2 placeholder-neutral-300 duration-200 focus:outline-hidden focus:ring-neutral-300 sm:text-sm"
                  id="password"
                  name="password" // Added name attribute
                  placeholder="••••••••"
                  type="password"
                  required
                  minLength={8}
                />
              </div>

              {isSignUp && (
                <div>
                  <label
                    className="mb-3 block font-medium text-black text-sm"
                    htmlFor="role"
                  >
                    I am signing up as
                  </label>
                  <select
                    className="block h-12 w-full appearance-none rounded-xl bg-white px-4 py-2 placeholder-neutral-300 duration-200 focus:outline-hidden focus:ring-neutral-300 sm:text-sm"
                    id="role"
                    name="role"
                    required
                  >
                    <option value="candidate">Candidate</option>
                    <option value="hr">HR Professional</option>
                  </select>
                </div>
              )}

              {isSignUp && (
                <div>
                  <label
                    className="mb-3 block font-medium text-black text-sm"
                    htmlFor="companyCode"
                  >
                    Company Code (HRs only)
                  </label>
                  <input
                    className="block h-12 w-full appearance-none rounded-xl bg-white px-4 py-2 placeholder-neutral-300 duration-200 focus:outline-hidden focus:ring-neutral-300 sm:text-sm"
                    id="companyCode"
                    name="companyCode"
                    placeholder="Enter company code"
                    type="text"
                  />
                </div>
              )}

              <div className="col-span-full">
                <div className="flex gap-2 items-center">
                  <button
                    className="inline-flex h-12 w-full items-center justify-center gap-3 rounded-xl bg-neutral-900 px-5 py-3 font-medium text-white duration-200 hover:bg-neutral-700 focus:ring-2 focus:ring-black focus:ring-offset-2"
                    type="submit"
                  >
                    {isSignUp ? "Sign Up" : "Sign In"}
                  </button>
                  <button
                    className="inline-flex h-12 w-full items-center justify-center gap-3 rounded-xl bg-gray-300 px-5 py-3 font-medium text-black duration-200 hover:bg-neutral-400 focus:ring-2 focus:ring-black focus:ring-offset-2"
                    type="button"
                    onClick={handleCancel}
                  >
                    Cancel
                  </button>
                </div>
              </div>
            </div>
            <div className="mt-6">
              <p className="mx-auto flex text-center font-medium text-black text-sm leading-tight">
                {isSignUp ? "Already have an account? " : "Need an account? "}
                <button
                  type="button"
                  className="ml-auto text-amber-500 hover:text-black"
                  onClick={() => setIsSignUp(!isSignUp)}
                >
                  {isSignUp ? "Sign In instead" : "Sign Up now"}
                </button>
              </p>
            </div>
          </form>
        </div>
      </div>
    </section>
  );
}

function GoogleIcon(props: Readonly<SVGProps<SVGSVGElement>>) {
  return (
    <svg
      height="100"
      viewBox="0 0 48 48"
      width="100"
      x="0px"
      xmlns="http://www.w3.org/2000/svg"
      y="0px"
      {...props}
    >
      <title>Google Logo</title>
      <path
        d="M43.611,20.083H42V20H24v8h11.303c-1.649,4.657-6.08,8-11.303,8c-6.627,0-12-5.373-12-12c0-6.627,5.373-12,12-12c3.059,0,5.842,1.154,7.961,3.039l5.657-5.657C34.046,6.053,29.268,4,24,4C12.955,4,4,12.955,4,24c0,11.045,8.955,20,20,20c11.045,0,20-8.955,20-20C44,22.659,43.862,21.35,43.611,20.083z"
        fill="#FFC107"
      />
      <path
        d="M6.306,14.691l6.571,4.819C14.655,15.108,18.961,12,24,12c3.059,0,5.842,1.154,7.961,3.039l5.657-5.657C34.046,6.053,29.268,4,24,4C16.318,4,9.656,8.337,6.306,14.691z"
        fill="#FF3D00"
      />
      <path
        d="M24,44c5.166,0,9.86-1.977,13.409-5.192l-6.19-5.238C29.211,35.091,26.715,36,24,36c-5.202,0-9.619-3.317-11.283-7.946l-6.522,5.025C9.505,39.556,16.227,44,24,44z"
        fill="#4CAF50"
      />
      <path
        d="M43.611,20.083H42V20H24v8h11.303c-0.792,2.237-2.231,4.166-4.087,5.571c0.001-0.001,0.002-0.001,0.003-0.002l6.19,5.238C36.971,39.205,44,34,44,24C44,22.659,43.862,21.35,43.611,20.083z"
        fill="#1976D2"
      />
    </svg>
  );
}
