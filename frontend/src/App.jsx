import { useEffect, useState } from "react";

const API_BASE = import.meta.env.VITE_API_BASE || "http://localhost:8000/api/v1";

export default function App() {
  const merchantId = 1;
  const [dashboard, setDashboard] = useState(null);
  const [amount, setAmount] = useState(1000);
  const [bankAccountId, setBankAccountId] = useState(1);
  const [error, setError] = useState("");

  async function refresh() {
    const response = await fetch(`${API_BASE}/merchants/${merchantId}/dashboard`);
    setDashboard(await response.json());
  }

  useEffect(() => {
    refresh();
    const timer = setInterval(refresh, 4000);
    return () => clearInterval(timer);
  }, []);

  async function submitPayout(event) {
    event.preventDefault();
    setError("");
    const response = await fetch(`${API_BASE}/payouts`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        "Idempotency-Key": crypto.randomUUID(),
      },
      body: JSON.stringify({
        merchant_id: merchantId,
        bank_account_id: Number(bankAccountId),
        amount_paise: Number(amount),
      }),
    });
    if (!response.ok) {
      const body = await response.json();
      setError(body.detail || JSON.stringify(body));
    }
    await refresh();
  }

  if (!dashboard) return <main className="p-8">Loading...</main>;

  return (
    <main className="p-8 max-w-3xl mx-auto space-y-4">
      <h1 className="text-2xl font-bold">Playto Merchant Dashboard</h1>
      <div className="grid grid-cols-2 gap-3">
        <div className="border rounded p-3">
          Available: {dashboard.balances.available_paise} paise
        </div>
        <div className="border rounded p-3">Held: {dashboard.balances.held_paise} paise</div>
      </div>

      <form onSubmit={submitPayout} className="border rounded p-4 space-y-2">
        <h2 className="font-semibold">Request payout</h2>
        <input
          className="border rounded p-2 w-full"
          value={amount}
          onChange={(e) => setAmount(e.target.value)}
        />
        <input
          className="border rounded p-2 w-full"
          value={bankAccountId}
          onChange={(e) => setBankAccountId(e.target.value)}
        />
        <button className="bg-black text-white px-3 py-2 rounded" type="submit">
          Submit
        </button>
        {error && <div className="text-red-600">{error}</div>}
      </form>

      <section>
        <h2 className="font-semibold mb-2">Payout history</h2>
        <ul className="space-y-2">
          {dashboard.payouts.map((payout) => (
            <li key={payout.id} className="border rounded p-2">
              #{payout.id} - {payout.status} - {payout.amount_paise} paise - attempts {payout.attempts}
            </li>
          ))}
        </ul>
      </section>
    </main>
  );
}
