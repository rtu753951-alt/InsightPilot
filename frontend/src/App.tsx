
import CustomersPage from "./pages/Customers";

export default function App() {
  return <CustomersPage />;
}

// export default function App() {
//   const [email, setEmail] = useState("test@example.com");
//   const [password, setPassword] = useState("test1234");
//   const [msg, setMsg] = useState<string>("");

//   async function onRegister() {
//     setMsg("Registering...");
//     try {
//       const u = await register(email, password);
//       setMsg(`✅ Registered: ${u.email}`);
//     } catch (e) {
//       setMsg(`❌ ${String(e)}`);
//     }
//   }

//   async function onLogin() {
//     setMsg("Logging in...");
//     try {
//       await login(email, password);
//       setMsg("✅ Logged in. Token saved.");
//     } catch (e) {
//       setMsg(`❌ ${String(e)}`);
//     }
//   }

//   async function onMe() {
//     setMsg("Fetching /me ...");
//     try {
//       const u = await me();
//       setMsg(`✅ Me: ${u.email} (id=${u.id})`);
//     } catch (e) {
//       setMsg(`❌ ${String(e)}`);
//     }
//   }

//   function onLogout() {
//     logout();
//     setMsg("✅ Logged out (token cleared).");
//   }

//   return (
//     <div style={{ padding: 24, fontFamily: "system-ui", maxWidth: 520 }}>
//       <h1>InsightPilot</h1>

//       <div style={{ display: "grid", gap: 8 }}>
//         <label>
//           Email
//           <input value={email} onChange={(e) => setEmail(e.target.value)} style={{ width: "100%" }} />
//         </label>
//         <label>
//           Password
//           <input
//             value={password}
//             onChange={(e) => setPassword(e.target.value)}
//             type="password"
//             style={{ width: "100%" }}
//           />
//         </label>

//         <div style={{ display: "flex", gap: 8, flexWrap: "wrap" }}>
//           <button onClick={onRegister}>Register</button>
//           <button onClick={onLogin}>Login</button>
//           <button onClick={onMe}>Me</button>
//           <button onClick={onLogout}>Logout</button>
//         </div>

//         <p>{msg}</p>
//       </div>
//     </div>
//   );

// }
