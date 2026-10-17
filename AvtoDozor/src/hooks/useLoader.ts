import { useCallback, useRef, useState } from 'react';
import { getErrorMessage } from '../api/client';
import { notify } from '../utils/notify';

/**
 * Загрузка данных для экрана: первичная загрузка, обновление «потянуть вниз» и защита
 * от устаревших ответов (если запрос повторили, берём результат только последнего).
 */
export function useLoader<T>(fetcher: () => Promise<T>, initial: T) {
  const [data, setData] = useState<T>(initial);
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);

  const fetcherRef = useRef(fetcher);
  fetcherRef.current = fetcher;
  const requestId = useRef(0);

  const reload = useCallback(async (pullToRefresh = false) => {
    const id = ++requestId.current;
    if (pullToRefresh) {
      setRefreshing(true);
    } else {
      setLoading(true);
    }
    try {
      const result = await fetcherRef.current();
      if (id === requestId.current) {
        setData(result);
      }
    } catch (error) {
      if (id === requestId.current) {
        notify(getErrorMessage(error), true);
      }
    } finally {
      if (id === requestId.current) {
        setLoading(false);
        setRefreshing(false);
      }
    }
  }, []);

  return { data, loading, refreshing, reload };
}
