import { render, screen } from '@testing-library/react';
import App from './App';

test('renders stock watchlist heading', () => {
  render(<App />);
  const heading = screen.getByText(/Stock Watchlist/i);
  expect(heading).toBeInTheDocument();
});
