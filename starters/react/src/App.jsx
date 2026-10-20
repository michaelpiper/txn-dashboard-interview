import { useEffect, useState } from 'react';

export default function App() {
  const [transactions, setTransactions] = useState([]);

  useEffect(() => {
    fetch('/api/transactions?page_size=500')
      .then((res) => res.json())
      .then((body) => setTransactions(body.data));
  }, []);

  // TODO: render the table, search, status filter, pagination,
  // a row action, and loading / empty / error states.
  return (
    <main style={{ fontFamily: 'system-ui, sans-serif', padding: 24 }}>
      <h1>Transactions</h1>
      <p>Loaded {transactions.length} transactions.</p>
    </main>
  );
}
