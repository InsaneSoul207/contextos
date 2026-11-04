import { useState, useEffect, useCallback, useRef } from "react";

interface UseQueryResult<T> {
  data: T | null;
  loading: boolean;
  error: string | null;
  refetch: () => Promise<void>;
}

export function useQuery<T>(
  key: string,
  fetcher: () => Promise<T>,
  options?: { enabled?: boolean }
): UseQueryResult<T> {
  const [data, setData] = useState<T | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const fetcherRef = useRef(fetcher);
  fetcherRef.current = fetcher;

  const enabled = options?.enabled ?? true;

  const fetchData = useCallback(async () => {
    if (!enabled) {
      setLoading(false);
      return;
    }
    setLoading(true);
    setError(null);
    try {
      const result = await fetcherRef.current();
      setData(result);
    } catch (err) {
      setError((err as Error).message);
    } finally {
      setLoading(false);
    }
  }, [enabled]);

  useEffect(() => {
    fetchData();
  }, [key, fetchData]);

  return { data, loading, error, refetch: fetchData };
}

interface UseMutationResult<T, V> {
  data: T | null;
  loading: boolean;
  error: string | null;
  mutate: (variables: V) => Promise<T | null>;
  reset: () => void;
}

export function useMutation<T, V = void>(
  fetcher: (variables: V) => Promise<T>
): UseMutationResult<T, V> {
  const [data, setData] = useState<T | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const mutate = useCallback(
    async (variables: V): Promise<T | null> => {
      setLoading(true);
      setError(null);
      try {
        const result = await fetcher(variables);
        setData(result);
        return result;
      } catch (err) {
        setError((err as Error).message);
        return null;
      } finally {
        setLoading(false);
      }
    },
    [fetcher]
  );

  const reset = useCallback(() => {
    setData(null);
    setError(null);
    setLoading(false);
  }, []);

  return { data, loading, error, mutate, reset };
}
