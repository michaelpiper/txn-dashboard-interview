import { useEffect, useState, useCallback } from 'react';

const PAGE_SIZE = 10;
const COLUMNS = ['ID', 'Amount', 'Currency', 'Customer Name', 'Flag Reason', 'Reference', 'Status'];

function TransactionItem({ transaction }) {
  return (
    <tr>
      <td>{transaction.id}</td>
      <td>{transaction.amount}</td>
      <td>{transaction.currency}</td>
      <td>{transaction.customer_name}</td>
      <td>{transaction.flag_reason ?? 'N/A'}</td>
      <td>{transaction.reference}</td>
      <td>{transaction.status}</td>
    </tr>
  );
}

export default function App() {
  const [transactions, setTransactions] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [currentPage, setCurrentPage] = useState(1);
  const [totalPages, setTotalPages] = useState(1);
  const [q, setQ] = useState('');

  const loadPage = useCallback(
    async (page) => {
      setLoading(true);
      setError(null);
      const params = new URLSearchParams({ page, page_size: PAGE_SIZE });
      if (q.trim()) params.set('q', q.trim());

      try {
        const res = await fetch(`/api/transactions?${params}`);
        const body = await res.json();
        if (!res.ok) throw new Error(body.message || `Request failed (${res.status})`);
        setTransactions(body.data);
        setTotalPages(body.total_pages);
        setCurrentPage(page);
      } catch (err) {
        setError(err);
      } finally {
        setLoading(false);
      }
    },
    [q]
  );

  useEffect(() => {
    loadPage(1);
    // Initial load only; later loads are triggered by search and pagination.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const handleSearch = (e) => {
    e.preventDefault();
    loadPage(1);
  };

  return (
    <main style={{ fontFamily: 'system-ui, sans-serif', padding: 24 }}>
      <h1>Transactions</h1>

      <form onSubmit={handleSearch} style={{ marginBottom: 16 }}>
        <input
          type="text"
          placeholder="Search by reference..."
          value={q}
          onChange={(e) => setQ(e.target.value)}
        />
        <button type="submit" disabled={loading}>
          Search
        </button>
      </form>

      {error && <p role="alert">Error: {error.message}</p>}

      <table>
        <thead>
          <tr>
            {COLUMNS.map((col) => (
              <th key={col}>{col}</th>
            ))}
          </tr>
        </thead>
        <tbody>
          {loading ? (
            <tr>
              <td colSpan={COLUMNS.length}>Loading...</td>
            </tr>
          ) : transactions.length === 0 ? (
            <tr>
              <td colSpan={COLUMNS.length}>No transactions found.</td>
            </tr>
          ) : (
            transactions.map((transaction) => (
              <TransactionItem key={transaction.id} transaction={transaction} />
            ))
          )}
        </tbody>
      </table>

      <nav style={{ marginTop: 16 }}>
        <button onClick={() => loadPage(currentPage - 1)} disabled={loading || currentPage <= 1}>
          Previous
        </button>
        <span style={{ margin: '0 12px' }}>
          Page {currentPage} of {totalPages}
        </span>
        <button onClick={() => loadPage(currentPage + 1)} disabled={loading || currentPage >= totalPages}>
          Next
        </button>
      </nav>
    </main>
  );
}
