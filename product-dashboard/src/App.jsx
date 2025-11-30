import { useState, useMemo, useEffect } from 'react';
import originalData from './data.json';
import trackingData from './tracking.json';

const STORAGE_KEY = 'scraper_product_edits';

const App = () => {
  const [searchTerm, setSearchTerm] = useState('');
  const [selectedBrand, setSelectedBrand] = useState('All');
  const [selectedView, setSelectedView] = useState('grid');
  const [selectedProduct, setSelectedProduct] = useState(null);
  const [editMode, setEditMode] = useState(false);
  const [editedFields, setEditedFields] = useState({});
  const [savedEdits, setSavedEdits] = useState({});
  const [showOnlyIncomplete, setShowOnlyIncomplete] = useState(false);
  const [activeTab, setActiveTab] = useState('products'); // 'products' or 'tracking'
  const [trackingFilter, setTrackingFilter] = useState('all');

  // Load saved edits from localStorage
  useEffect(() => {
    const saved = localStorage.getItem(STORAGE_KEY);
    if (saved) {
      setSavedEdits(JSON.parse(saved));
    }
  }, []);

  // Merge original data with saved edits
  const productsData = useMemo(() => {
    return originalData.map(product => {
      const edits = savedEdits[product.source_url];
      if (edits) {
        return { ...product, ...edits, _hasEdits: true };
      }
      return product;
    });
  }, [savedEdits]);

  const brands = ['All', ...new Set(productsData.map(p => p.brand))].sort();

  const urlStats = useMemo(() => {
    const byDomain = {};
    productsData.forEach(p => {
      try {
        const url = new URL(p.source_url);
        const domain = url.hostname;
        if (!byDomain[domain]) {
          byDomain[domain] = { count: 0, products: [], incomplete: 0 };
        }
        byDomain[domain].count++;
        byDomain[domain].products.push(p);
        if (isIncomplete(p)) {
          byDomain[domain].incomplete++;
        }
      } catch (e) {
        // ignore
      }
    });
    return byDomain;
  }, [productsData]);

  const isIncomplete = (product) => {
    return !product.product_name?.trim() ||
           !product.description?.trim() ||
           !product.ingredients_list?.trim();
  };

  const getCompletionPercent = (product) => {
    const fields = ['product_name', 'description', 'ingredients_list', 'usage_instructions', 'brand', 'product_type'];
    const filled = fields.filter(f => product[f]?.trim()).length;
    return Math.round((filled / fields.length) * 100);
  };

  const filteredProducts = useMemo(() => {
    return productsData.filter(product => {
      const matchesSearch =
        product.product_name?.toLowerCase().includes(searchTerm.toLowerCase()) ||
        product.description?.toLowerCase().includes(searchTerm.toLowerCase()) ||
        product.source_url?.toLowerCase().includes(searchTerm.toLowerCase());
      const matchesBrand = selectedBrand === 'All' || product.brand === selectedBrand;
      const matchesIncomplete = !showOnlyIncomplete || isIncomplete(product);
      return matchesSearch && matchesBrand && matchesIncomplete;
    });
  }, [searchTerm, selectedBrand, productsData, showOnlyIncomplete]);

  const incompleteCount = productsData.filter(isIncomplete).length;

  const getStatusColor = (product) => {
    if (product._hasEdits) return 'blue';
    if (!product.product_name || product.product_name.trim() === '') return 'red';
    if (!product.description || product.description.trim() === '') return 'yellow';
    if (!product.ingredients_list || product.ingredients_list.trim() === '') return 'orange';
    return 'green';
  };

  const openProductModal = (product) => {
    setSelectedProduct(product);
    setEditedFields({});
    setEditMode(false);
  };

  const handleFieldChange = (field, value) => {
    setEditedFields(prev => ({ ...prev, [field]: value }));
  };

  const saveEdits = () => {
    if (!selectedProduct) return;

    const newEdits = {
      ...savedEdits,
      [selectedProduct.source_url]: {
        ...(savedEdits[selectedProduct.source_url] || {}),
        ...editedFields,
        _editedAt: new Date().toISOString()
      }
    };

    localStorage.setItem(STORAGE_KEY, JSON.stringify(newEdits));
    setSavedEdits(newEdits);
    setEditMode(false);
    setEditedFields({});

    // Update selected product with new data
    setSelectedProduct(prev => ({ ...prev, ...editedFields, _hasEdits: true }));
  };

  const exportData = () => {
    const dataStr = JSON.stringify(productsData, null, 2);
    const blob = new Blob([dataStr], { type: 'application/json' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `produtos_capilares_editados_${new Date().toISOString().split('T')[0]}.json`;
    a.click();
    URL.revokeObjectURL(url);
  };

  const clearAllEdits = () => {
    if (confirm('Tem certeza que deseja limpar todas as edicoes salvas?')) {
      localStorage.removeItem(STORAGE_KEY);
      setSavedEdits({});
    }
  };

  const EditableField = ({ label, field, value, multiline = false }) => {
    const isEmpty = !value?.trim();
    const currentValue = editedFields[field] !== undefined ? editedFields[field] : value;

    if (!editMode) {
      return (
        <div style={{ marginBottom: '15px' }}>
          <label style={{
            display: 'block',
            fontSize: '12px',
            color: '#666',
            marginBottom: '5px',
            fontWeight: '500'
          }}>
            {label}
            {isEmpty && (
              <span style={{
                marginLeft: '8px',
                padding: '2px 6px',
                backgroundColor: '#ffebee',
                color: '#c62828',
                borderRadius: '3px',
                fontSize: '10px'
              }}>
                VAZIO
              </span>
            )}
          </label>
          <div style={{
            padding: '10px',
            backgroundColor: isEmpty ? '#fff8e1' : '#f5f5f5',
            borderRadius: '6px',
            border: isEmpty ? '1px dashed #ffa000' : '1px solid #e0e0e0',
            minHeight: multiline ? '60px' : 'auto',
            fontSize: '13px',
            color: isEmpty ? '#999' : '#333'
          }}>
            {value || <em>Clique em Editar para preencher</em>}
          </div>
        </div>
      );
    }

    return (
      <div style={{ marginBottom: '15px' }}>
        <label style={{
          display: 'block',
          fontSize: '12px',
          color: '#1976d2',
          marginBottom: '5px',
          fontWeight: '600'
        }}>
          {label}
        </label>
        {multiline ? (
          <textarea
            value={currentValue || ''}
            onChange={(e) => handleFieldChange(field, e.target.value)}
            style={{
              width: '100%',
              padding: '10px',
              border: '2px solid #1976d2',
              borderRadius: '6px',
              fontSize: '13px',
              minHeight: '80px',
              resize: 'vertical',
              fontFamily: 'inherit'
            }}
          />
        ) : (
          <input
            type="text"
            value={currentValue || ''}
            onChange={(e) => handleFieldChange(field, e.target.value)}
            style={{
              width: '100%',
              padding: '10px',
              border: '2px solid #1976d2',
              borderRadius: '6px',
              fontSize: '13px'
            }}
          />
        )}
      </div>
    );
  };

  return (
    <div style={{
      minHeight: '100vh',
      backgroundColor: '#f5f5f5',
      fontFamily: 'system-ui, -apple-system, sans-serif'
    }}>
      {/* Header */}
      <header style={{
        backgroundColor: '#1a1a2e',
        color: 'white',
        padding: '20px 40px',
      }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexWrap: 'wrap', gap: '15px' }}>
          <div>
            <h1 style={{ margin: 0, fontSize: '24px', fontWeight: 'bold' }}>
              Scraper Dashboard - Produtos Capilares
            </h1>
            <p style={{ margin: '8px 0 0', opacity: 0.8, fontSize: '14px' }}>
              {trackingData.total_brands} marcas | {productsData.length} produtos coletados | {trackingData.brands.filter(b => b.status === 'scraped').length} sites processados
            </p>
          </div>
          <div style={{ display: 'flex', gap: '10px' }}>
            <button
              onClick={exportData}
              style={{
                padding: '10px 20px',
                backgroundColor: '#4caf50',
                color: 'white',
                border: 'none',
                borderRadius: '6px',
                cursor: 'pointer',
                fontSize: '14px',
                fontWeight: '500'
              }}
            >
              Exportar JSON
            </button>
            {Object.keys(savedEdits).length > 0 && (
              <button
                onClick={clearAllEdits}
                style={{
                  padding: '10px 20px',
                  backgroundColor: '#f44336',
                  color: 'white',
                  border: 'none',
                  borderRadius: '6px',
                  cursor: 'pointer',
                  fontSize: '14px'
                }}
              >
                Limpar Edicoes
              </button>
            )}
          </div>
        </div>

        {/* Tabs */}
        <div style={{ display: 'flex', gap: '0', marginTop: '20px' }}>
          <button
            onClick={() => setActiveTab('products')}
            style={{
              padding: '12px 24px',
              backgroundColor: activeTab === 'products' ? 'white' : 'transparent',
              color: activeTab === 'products' ? '#1a1a2e' : 'white',
              border: 'none',
              borderRadius: '8px 8px 0 0',
              cursor: 'pointer',
              fontSize: '14px',
              fontWeight: '600'
            }}
          >
            Produtos ({productsData.length})
          </button>
          <button
            onClick={() => setActiveTab('tracking')}
            style={{
              padding: '12px 24px',
              backgroundColor: activeTab === 'tracking' ? 'white' : 'transparent',
              color: activeTab === 'tracking' ? '#1a1a2e' : 'white',
              border: 'none',
              borderRadius: '8px 8px 0 0',
              cursor: 'pointer',
              fontSize: '14px',
              fontWeight: '600'
            }}
          >
            Tracking URLs ({trackingData.brands.length})
          </button>
        </div>
      </header>

      <div style={{ padding: '20px 40px 40px' }}>

        {/* Tracking Tab */}
        {activeTab === 'tracking' && (
          <div>
            {/* Tracking Stats */}
            <div style={{
              display: 'grid',
              gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))',
              gap: '15px',
              marginBottom: '20px'
            }}>
              <div style={{ backgroundColor: '#e8f5e9', padding: '20px', borderRadius: '8px', textAlign: 'center' }}>
                <div style={{ fontSize: '32px', fontWeight: 'bold', color: '#2e7d32' }}>
                  {trackingData.brands.filter(b => b.status === 'scraped').length}
                </div>
                <div style={{ color: '#666', fontSize: '14px' }}>Sites Processados</div>
              </div>
              <div style={{ backgroundColor: '#fff3e0', padding: '20px', borderRadius: '8px', textAlign: 'center' }}>
                <div style={{ fontSize: '32px', fontWeight: 'bold', color: '#ef6c00' }}>
                  {trackingData.brands.filter(b => b.status === 'pending').length}
                </div>
                <div style={{ color: '#666', fontSize: '14px' }}>Aguardando</div>
              </div>
              <div style={{ backgroundColor: '#fce4ec', padding: '20px', borderRadius: '8px', textAlign: 'center' }}>
                <div style={{ fontSize: '32px', fontWeight: 'bold', color: '#c62828' }}>
                  {trackingData.brands.filter(b => b.status === 'js_required').length}
                </div>
                <div style={{ color: '#666', fontSize: '14px' }}>Requer JavaScript</div>
              </div>
              <div style={{ backgroundColor: '#e3f2fd', padding: '20px', borderRadius: '8px', textAlign: 'center' }}>
                <div style={{ fontSize: '32px', fontWeight: 'bold', color: '#1565c0' }}>
                  {trackingData.brands.reduce((sum, b) => sum + (b.products || 0), 0)}
                </div>
                <div style={{ color: '#666', fontSize: '14px' }}>Total Produtos</div>
              </div>
            </div>

            {/* Tracking Filters */}
            <div style={{
              backgroundColor: 'white',
              padding: '15px 20px',
              borderRadius: '8px',
              marginBottom: '20px',
              display: 'flex',
              gap: '10px',
              flexWrap: 'wrap'
            }}>
              {['all', 'scraped', 'pending', 'js_required'].map(filter => (
                <button
                  key={filter}
                  onClick={() => setTrackingFilter(filter)}
                  style={{
                    padding: '8px 16px',
                    borderRadius: '20px',
                    border: 'none',
                    backgroundColor: trackingFilter === filter ? '#1a1a2e' : '#f0f0f0',
                    color: trackingFilter === filter ? 'white' : '#333',
                    cursor: 'pointer',
                    fontSize: '13px'
                  }}
                >
                  {filter === 'all' ? 'Todos' :
                   filter === 'scraped' ? 'Processados' :
                   filter === 'pending' ? 'Pendentes' : 'JavaScript'}
                </button>
              ))}
            </div>

            {/* Tracking Table */}
            <div style={{
              backgroundColor: 'white',
              borderRadius: '8px',
              overflow: 'auto',
              boxShadow: '0 1px 3px rgba(0,0,0,0.1)'
            }}>
              <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: '13px' }}>
                <thead>
                  <tr style={{ backgroundColor: '#f8f9fa' }}>
                    <th style={{ padding: '12px', textAlign: 'left', borderBottom: '2px solid #dee2e6' }}>Status</th>
                    <th style={{ padding: '12px', textAlign: 'left', borderBottom: '2px solid #dee2e6' }}>Marca</th>
                    <th style={{ padding: '12px', textAlign: 'center', borderBottom: '2px solid #dee2e6' }}>Produtos</th>
                    <th style={{ padding: '12px', textAlign: 'center', borderBottom: '2px solid #dee2e6' }}>Ingredientes</th>
                    <th style={{ padding: '12px', textAlign: 'left', borderBottom: '2px solid #dee2e6' }}>URL</th>
                  </tr>
                </thead>
                <tbody>
                  {trackingData.brands
                    .filter(b => trackingFilter === 'all' || b.status === trackingFilter)
                    .map((brand, idx) => (
                    <tr key={idx} style={{ borderBottom: '1px solid #eee' }}>
                      <td style={{ padding: '12px' }}>
                        <span style={{
                          padding: '4px 10px',
                          borderRadius: '12px',
                          fontSize: '11px',
                          fontWeight: '600',
                          backgroundColor: brand.status === 'scraped' ? '#e8f5e9' :
                                          brand.status === 'pending' ? '#fff3e0' :
                                          brand.status === 'js_required' ? '#fce4ec' : '#f5f5f5',
                          color: brand.status === 'scraped' ? '#2e7d32' :
                                brand.status === 'pending' ? '#ef6c00' :
                                brand.status === 'js_required' ? '#c62828' : '#666'
                        }}>
                          {brand.status === 'scraped' ? 'OK' :
                           brand.status === 'pending' ? 'PENDENTE' :
                           brand.status === 'js_required' ? 'JS' : brand.status.toUpperCase()}
                        </span>
                      </td>
                      <td style={{ padding: '12px', fontWeight: '500' }}>{brand.name}</td>
                      <td style={{ padding: '12px', textAlign: 'center' }}>
                        <span style={{
                          fontWeight: brand.products > 0 ? 'bold' : 'normal',
                          color: brand.products > 0 ? '#2e7d32' : '#999'
                        }}>
                          {brand.products}
                        </span>
                      </td>
                      <td style={{ padding: '12px', textAlign: 'center' }}>
                        {brand.has_ingredients ? (
                          <span style={{ color: '#4caf50', fontSize: '16px' }}>✓</span>
                        ) : (
                          <span style={{ color: '#ccc', fontSize: '16px' }}>-</span>
                        )}
                      </td>
                      <td style={{ padding: '12px' }}>
                        <a
                          href={brand.url}
                          target="_blank"
                          rel="noopener noreferrer"
                          style={{ color: '#1976d2', textDecoration: 'none', fontSize: '12px' }}
                        >
                          {brand.url.length > 50 ? brand.url.substring(0, 50) + '...' : brand.url}
                        </a>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        )}

        {/* Products Tab */}
        {activeTab === 'products' && (
          <>
        {/* URL Stats */}
        <div style={{
          backgroundColor: 'white',
          borderRadius: '8px',
          padding: '20px',
          marginBottom: '20px',
          boxShadow: '0 1px 3px rgba(0,0,0,0.1)'
        }}>
          <h2 style={{ margin: '0 0 15px', fontSize: '18px', fontWeight: '600' }}>
            Status por Dominio
          </h2>
          <div style={{ display: 'flex', flexWrap: 'wrap', gap: '10px' }}>
            {Object.entries(urlStats).map(([domain, data]) => (
              <div key={domain} style={{
                backgroundColor: data.incomplete > 0 ? '#fff3e0' : '#e8f5e9',
                border: `1px solid ${data.incomplete > 0 ? '#ffcc80' : '#a5d6a7'}`,
                borderRadius: '6px',
                padding: '10px 15px',
                fontSize: '14px'
              }}>
                <strong>{domain}</strong>
                <span style={{
                  marginLeft: '10px',
                  backgroundColor: '#4caf50',
                  color: 'white',
                  padding: '2px 8px',
                  borderRadius: '10px',
                  fontSize: '12px'
                }}>
                  {data.count} produtos
                </span>
                {data.incomplete > 0 && (
                  <span style={{
                    marginLeft: '5px',
                    backgroundColor: '#ff9800',
                    color: 'white',
                    padding: '2px 8px',
                    borderRadius: '10px',
                    fontSize: '12px'
                  }}>
                    {data.incomplete} incompletos
                  </span>
                )}
              </div>
            ))}
          </div>
        </div>

        {/* Filters */}
        <div style={{
          backgroundColor: 'white',
          borderRadius: '8px',
          padding: '20px',
          marginBottom: '20px',
          boxShadow: '0 1px 3px rgba(0,0,0,0.1)',
          display: 'flex',
          gap: '15px',
          alignItems: 'center',
          flexWrap: 'wrap'
        }}>
          <div style={{ flex: 1, minWidth: '200px' }}>
            <input
              type="text"
              placeholder="Buscar produtos ou URLs..."
              value={searchTerm}
              onChange={(e) => setSearchTerm(e.target.value)}
              style={{
                width: '100%',
                padding: '10px 15px',
                border: '1px solid #ddd',
                borderRadius: '6px',
                fontSize: '14px'
              }}
            />
          </div>
          <div>
            <select
              value={selectedBrand}
              onChange={(e) => setSelectedBrand(e.target.value)}
              style={{
                padding: '10px 15px',
                border: '1px solid #ddd',
                borderRadius: '6px',
                fontSize: '14px',
                backgroundColor: 'white'
              }}
            >
              {brands.map(brand => (
                <option key={brand} value={brand}>{brand}</option>
              ))}
            </select>
          </div>
          <label style={{
            display: 'flex',
            alignItems: 'center',
            gap: '8px',
            cursor: 'pointer',
            padding: '10px 15px',
            backgroundColor: showOnlyIncomplete ? '#fff3e0' : '#f5f5f5',
            borderRadius: '6px',
            border: showOnlyIncomplete ? '1px solid #ff9800' : '1px solid #ddd'
          }}>
            <input
              type="checkbox"
              checked={showOnlyIncomplete}
              onChange={(e) => setShowOnlyIncomplete(e.target.checked)}
              style={{ width: '16px', height: '16px' }}
            />
            <span style={{ fontSize: '14px' }}>Apenas incompletos ({incompleteCount})</span>
          </label>
          <div style={{ display: 'flex', gap: '5px' }}>
            <button
              onClick={() => setSelectedView('grid')}
              style={{
                padding: '10px 15px',
                border: '1px solid #ddd',
                borderRadius: '6px',
                backgroundColor: selectedView === 'grid' ? '#1a1a2e' : 'white',
                color: selectedView === 'grid' ? 'white' : '#333',
                cursor: 'pointer'
              }}
            >
              Grid
            </button>
            <button
              onClick={() => setSelectedView('table')}
              style={{
                padding: '10px 15px',
                border: '1px solid #ddd',
                borderRadius: '6px',
                backgroundColor: selectedView === 'table' ? '#1a1a2e' : 'white',
                color: selectedView === 'table' ? 'white' : '#333',
                cursor: 'pointer'
              }}
            >
              Tabela
            </button>
          </div>
          <div style={{ fontSize: '14px', color: '#666' }}>
            {filteredProducts.length} resultados
          </div>
        </div>

        {/* Legend */}
        <div style={{
          backgroundColor: 'white',
          borderRadius: '8px',
          padding: '15px 20px',
          marginBottom: '20px',
          boxShadow: '0 1px 3px rgba(0,0,0,0.1)',
          display: 'flex',
          gap: '20px',
          flexWrap: 'wrap',
          fontSize: '13px'
        }}>
          <span><strong>Legenda:</strong></span>
          <span style={{ display: 'flex', alignItems: 'center', gap: '5px' }}>
            <span style={{ width: '12px', height: '12px', borderRadius: '50%', backgroundColor: '#4caf50' }}></span>
            Completo
          </span>
          <span style={{ display: 'flex', alignItems: 'center', gap: '5px' }}>
            <span style={{ width: '12px', height: '12px', borderRadius: '50%', backgroundColor: '#ff9800' }}></span>
            Falta ingredientes
          </span>
          <span style={{ display: 'flex', alignItems: 'center', gap: '5px' }}>
            <span style={{ width: '12px', height: '12px', borderRadius: '50%', backgroundColor: '#ffc107' }}></span>
            Falta descricao
          </span>
          <span style={{ display: 'flex', alignItems: 'center', gap: '5px' }}>
            <span style={{ width: '12px', height: '12px', borderRadius: '50%', backgroundColor: '#f44336' }}></span>
            Falta nome
          </span>
          <span style={{ display: 'flex', alignItems: 'center', gap: '5px' }}>
            <span style={{ width: '12px', height: '12px', borderRadius: '50%', backgroundColor: '#2196f3' }}></span>
            Editado manualmente
          </span>
        </div>

        {/* Table View */}
        {selectedView === 'table' && (
          <div style={{
            backgroundColor: 'white',
            borderRadius: '8px',
            boxShadow: '0 1px 3px rgba(0,0,0,0.1)',
            overflow: 'auto'
          }}>
            <table style={{
              width: '100%',
              borderCollapse: 'collapse',
              fontSize: '13px'
            }}>
              <thead>
                <tr style={{ backgroundColor: '#f8f9fa' }}>
                  <th style={{ padding: '12px', textAlign: 'left', borderBottom: '2px solid #dee2e6' }}>Status</th>
                  <th style={{ padding: '12px', textAlign: 'left', borderBottom: '2px solid #dee2e6' }}>%</th>
                  <th style={{ padding: '12px', textAlign: 'left', borderBottom: '2px solid #dee2e6' }}>Marca</th>
                  <th style={{ padding: '12px', textAlign: 'left', borderBottom: '2px solid #dee2e6' }}>Produto</th>
                  <th style={{ padding: '12px', textAlign: 'left', borderBottom: '2px solid #dee2e6' }}>Tipo</th>
                  <th style={{ padding: '12px', textAlign: 'left', borderBottom: '2px solid #dee2e6' }}>URL</th>
                  <th style={{ padding: '12px', textAlign: 'center', borderBottom: '2px solid #dee2e6' }}>Acao</th>
                </tr>
              </thead>
              <tbody>
                {filteredProducts.map((product, idx) => {
                  const status = getStatusColor(product);
                  const completion = getCompletionPercent(product);
                  return (
                    <tr
                      key={idx}
                      style={{
                        borderBottom: '1px solid #eee',
                        backgroundColor: product._hasEdits ? '#e3f2fd' : 'white'
                      }}
                    >
                      <td style={{ padding: '12px' }}>
                        <span style={{
                          display: 'inline-block',
                          width: '12px',
                          height: '12px',
                          borderRadius: '50%',
                          backgroundColor: status === 'green' ? '#4caf50' :
                                          status === 'yellow' ? '#ffc107' :
                                          status === 'orange' ? '#ff9800' :
                                          status === 'blue' ? '#2196f3' : '#f44336'
                        }}/>
                      </td>
                      <td style={{ padding: '12px' }}>
                        <div style={{
                          width: '50px',
                          height: '6px',
                          backgroundColor: '#e0e0e0',
                          borderRadius: '3px',
                          overflow: 'hidden'
                        }}>
                          <div style={{
                            width: `${completion}%`,
                            height: '100%',
                            backgroundColor: completion === 100 ? '#4caf50' : completion >= 50 ? '#ff9800' : '#f44336'
                          }}/>
                        </div>
                        <span style={{ fontSize: '11px', color: '#666' }}>{completion}%</span>
                      </td>
                      <td style={{ padding: '12px', fontWeight: '500' }}>{product.brand || '-'}</td>
                      <td style={{ padding: '12px', maxWidth: '250px' }}>
                        {product.product_name || <em style={{ color: '#f44336' }}>Sem nome</em>}
                      </td>
                      <td style={{ padding: '12px' }}>{product.product_type || '-'}</td>
                      <td style={{ padding: '12px' }}>
                        <a
                          href={product.source_url}
                          target="_blank"
                          rel="noopener noreferrer"
                          style={{ color: '#1976d2', textDecoration: 'none', fontSize: '12px' }}
                        >
                          {product.source_url?.substring(0, 40)}...
                        </a>
                      </td>
                      <td style={{ padding: '12px', textAlign: 'center' }}>
                        <button
                          onClick={() => openProductModal(product)}
                          style={{
                            padding: '6px 12px',
                            backgroundColor: isIncomplete(product) ? '#ff9800' : '#1976d2',
                            color: 'white',
                            border: 'none',
                            borderRadius: '4px',
                            cursor: 'pointer',
                            fontSize: '12px'
                          }}
                        >
                          {isIncomplete(product) ? 'Preencher' : 'Ver/Editar'}
                        </button>
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        )}

        {/* Grid View */}
        {selectedView === 'grid' && (
          <div style={{
            display: 'grid',
            gridTemplateColumns: 'repeat(auto-fill, minmax(280px, 1fr))',
            gap: '20px'
          }}>
            {filteredProducts.map((product, idx) => {
              const status = getStatusColor(product);
              const completion = getCompletionPercent(product);
              const statusColors = {
                green: '#4caf50',
                yellow: '#ffc107',
                orange: '#ff9800',
                red: '#f44336',
                blue: '#2196f3'
              };
              return (
                <div
                  key={idx}
                  onClick={() => openProductModal(product)}
                  style={{
                    backgroundColor: 'white',
                    borderRadius: '8px',
                    boxShadow: '0 1px 3px rgba(0,0,0,0.1)',
                    overflow: 'hidden',
                    cursor: 'pointer',
                    border: `3px solid ${statusColors[status]}`,
                    transition: 'transform 0.2s, box-shadow 0.2s',
                    position: 'relative'
                  }}
                  onMouseOver={(e) => {
                    e.currentTarget.style.transform = 'translateY(-2px)';
                    e.currentTarget.style.boxShadow = '0 4px 12px rgba(0,0,0,0.15)';
                  }}
                  onMouseOut={(e) => {
                    e.currentTarget.style.transform = 'translateY(0)';
                    e.currentTarget.style.boxShadow = '0 1px 3px rgba(0,0,0,0.1)';
                  }}
                >
                  {/* Completion bar */}
                  <div style={{
                    height: '4px',
                    backgroundColor: '#e0e0e0'
                  }}>
                    <div style={{
                      width: `${completion}%`,
                      height: '100%',
                      backgroundColor: statusColors[status]
                    }}/>
                  </div>

                  {product._hasEdits && (
                    <div style={{
                      position: 'absolute',
                      top: '10px',
                      right: '10px',
                      backgroundColor: '#2196f3',
                      color: 'white',
                      padding: '3px 8px',
                      borderRadius: '4px',
                      fontSize: '10px',
                      fontWeight: 'bold'
                    }}>
                      EDITADO
                    </div>
                  )}

                  <div style={{
                    height: '120px',
                    backgroundColor: '#f8f9fa',
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'center',
                    overflow: 'hidden'
                  }}>
                    {product.image_front_url ? (
                      <img
                        src={product.image_front_url}
                        alt={product.product_name}
                        style={{ maxHeight: '100%', maxWidth: '100%', objectFit: 'contain' }}
                        onError={(e) => { e.target.style.display = 'none'; }}
                      />
                    ) : (
                      <span style={{ color: '#999' }}>Sem imagem</span>
                    )}
                  </div>
                  <div style={{ padding: '15px' }}>
                    <div style={{
                      fontSize: '11px',
                      color: '#666',
                      textTransform: 'uppercase',
                      marginBottom: '5px'
                    }}>
                      {product.brand || <span style={{ color: '#f44336' }}>Marca?</span>}
                    </div>
                    <h3 style={{
                      margin: '0 0 10px',
                      fontSize: '14px',
                      fontWeight: '600',
                      lineHeight: '1.3',
                      color: product.product_name ? '#333' : '#f44336'
                    }}>
                      {product.product_name || 'NOME NAO ENCONTRADO'}
                    </h3>

                    {/* Missing fields indicator */}
                    <div style={{ display: 'flex', gap: '5px', flexWrap: 'wrap', marginBottom: '10px' }}>
                      {!product.description?.trim() && (
                        <span style={{
                          padding: '2px 6px',
                          borderRadius: '3px',
                          fontSize: '10px',
                          backgroundColor: '#ffebee',
                          color: '#c62828'
                        }}>
                          Falta descricao
                        </span>
                      )}
                      {!product.ingredients_list?.trim() && (
                        <span style={{
                          padding: '2px 6px',
                          borderRadius: '3px',
                          fontSize: '10px',
                          backgroundColor: '#fff3e0',
                          color: '#e65100'
                        }}>
                          Falta ingredientes
                        </span>
                      )}
                      {product.description?.trim() && product.ingredients_list?.trim() && (
                        <span style={{
                          padding: '2px 6px',
                          borderRadius: '3px',
                          fontSize: '10px',
                          backgroundColor: '#e8f5e9',
                          color: '#2e7d32'
                        }}>
                          Dados completos
                        </span>
                      )}
                    </div>

                    <div style={{ fontSize: '11px', color: '#888' }}>
                      {(() => {
                        try {
                          return new URL(product.source_url).hostname;
                        } catch {
                          return 'URL invalida';
                        }
                      })()}
                    </div>
                  </div>
                </div>
              );
            })}
          </div>
        )}

        {/* Product Detail/Edit Modal */}
        {selectedProduct && (
          <div
            style={{
              position: 'fixed',
              top: 0,
              left: 0,
              right: 0,
              bottom: 0,
              backgroundColor: 'rgba(0,0,0,0.5)',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              zIndex: 1000,
              padding: '20px'
            }}
            onClick={() => { setSelectedProduct(null); setEditMode(false); setEditedFields({}); }}
          >
            <div
              style={{
                backgroundColor: 'white',
                borderRadius: '12px',
                maxWidth: '900px',
                maxHeight: '90vh',
                overflow: 'auto',
                width: '100%'
              }}
              onClick={(e) => e.stopPropagation()}
            >
              {/* Modal Header */}
              <div style={{
                padding: '20px',
                borderBottom: '1px solid #eee',
                backgroundColor: editMode ? '#e3f2fd' : 'white',
                borderRadius: '12px 12px 0 0'
              }}>
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'start' }}>
                  <div>
                    <div style={{ fontSize: '12px', color: '#666', marginBottom: '5px' }}>
                      {selectedProduct.brand || 'Marca nao identificada'}
                    </div>
                    <h2 style={{ margin: 0, fontSize: '20px' }}>
                      {selectedProduct.product_name || 'Produto sem nome'}
                    </h2>
                    {selectedProduct._hasEdits && (
                      <span style={{
                        display: 'inline-block',
                        marginTop: '8px',
                        padding: '3px 10px',
                        backgroundColor: '#2196f3',
                        color: 'white',
                        borderRadius: '4px',
                        fontSize: '11px'
                      }}>
                        Editado em {new Date(savedEdits[selectedProduct.source_url]?._editedAt).toLocaleString('pt-BR')}
                      </span>
                    )}
                  </div>
                  <div style={{ display: 'flex', gap: '10px' }}>
                    {!editMode ? (
                      <button
                        onClick={() => setEditMode(true)}
                        style={{
                          padding: '10px 20px',
                          backgroundColor: '#1976d2',
                          color: 'white',
                          border: 'none',
                          borderRadius: '6px',
                          cursor: 'pointer',
                          fontSize: '14px',
                          fontWeight: '500'
                        }}
                      >
                        Editar
                      </button>
                    ) : (
                      <>
                        <button
                          onClick={() => { setEditMode(false); setEditedFields({}); }}
                          style={{
                            padding: '10px 20px',
                            backgroundColor: '#9e9e9e',
                            color: 'white',
                            border: 'none',
                            borderRadius: '6px',
                            cursor: 'pointer',
                            fontSize: '14px'
                          }}
                        >
                          Cancelar
                        </button>
                        <button
                          onClick={saveEdits}
                          style={{
                            padding: '10px 20px',
                            backgroundColor: '#4caf50',
                            color: 'white',
                            border: 'none',
                            borderRadius: '6px',
                            cursor: 'pointer',
                            fontSize: '14px',
                            fontWeight: '500'
                          }}
                        >
                          Salvar
                        </button>
                      </>
                    )}
                    <button
                      onClick={() => { setSelectedProduct(null); setEditMode(false); setEditedFields({}); }}
                      style={{
                        background: 'none',
                        border: 'none',
                        fontSize: '24px',
                        cursor: 'pointer',
                        color: '#666',
                        padding: '0 10px'
                      }}
                    >
                      x
                    </button>
                  </div>
                </div>
              </div>

              <div style={{ padding: '20px' }}>
                {/* URL */}
                <div style={{ marginBottom: '20px', padding: '10px', backgroundColor: '#f5f5f5', borderRadius: '6px' }}>
                  <label style={{ fontSize: '12px', color: '#666' }}>URL de Origem:</label>
                  <a
                    href={selectedProduct.source_url}
                    target="_blank"
                    rel="noopener noreferrer"
                    style={{ display: 'block', color: '#1976d2', wordBreak: 'break-all', fontSize: '13px', marginTop: '5px' }}
                  >
                    {selectedProduct.source_url}
                  </a>
                </div>

                {/* Editable Fields */}
                <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '20px' }}>
                  <EditableField
                    label="Nome do Produto"
                    field="product_name"
                    value={selectedProduct.product_name}
                  />
                  <EditableField
                    label="Marca"
                    field="brand"
                    value={selectedProduct.brand}
                  />
                </div>

                <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '20px' }}>
                  <EditableField
                    label="Tipo de Produto"
                    field="product_type"
                    value={selectedProduct.product_type}
                  />
                  <EditableField
                    label="Tipo de Cabelo"
                    field="hair_type_declared"
                    value={selectedProduct.hair_type_declared}
                  />
                </div>

                <EditableField
                  label="Descricao"
                  field="description"
                  value={selectedProduct.description}
                  multiline
                />

                <EditableField
                  label="Ingredientes"
                  field="ingredients_list"
                  value={selectedProduct.ingredients_list}
                  multiline
                />

                <EditableField
                  label="Modo de Uso"
                  field="usage_instructions"
                  value={selectedProduct.usage_instructions}
                  multiline
                />

                {/* Non-editable info */}
                <div style={{
                  display: 'grid',
                  gridTemplateColumns: 'repeat(3, 1fr)',
                  gap: '15px',
                  marginTop: '20px',
                  padding: '15px',
                  backgroundColor: '#f5f5f5',
                  borderRadius: '8px'
                }}>
                  <div>
                    <label style={{ fontSize: '11px', color: '#666' }}>Fase Cronograma</label>
                    <p style={{ margin: '5px 0 0', fontWeight: 'bold' }}>{selectedProduct.cronograma_fase || 'N/A'}</p>
                  </div>
                  <div>
                    <label style={{ fontSize: '11px', color: '#666' }}>Cabelos Finos</label>
                    <p style={{ margin: '5px 0 0', fontWeight: 'bold' }}>{selectedProduct.adequacao_cabelos_finos || 'N/A'}</p>
                  </div>
                  <div>
                    <label style={{ fontSize: '11px', color: '#666' }}>pH</label>
                    <p style={{ margin: '5px 0 0', fontWeight: 'bold' }}>{selectedProduct.ph || 'N/A'}</p>
                  </div>
                </div>

                {/* Claims */}
                <div style={{ marginTop: '20px' }}>
                  <label style={{ fontSize: '12px', color: '#666', marginBottom: '10px', display: 'block' }}>Claims Detectados</label>
                  <div style={{ display: 'flex', gap: '8px', flexWrap: 'wrap' }}>
                    {selectedProduct.claim_sem_sulfato && <span style={{ padding: '4px 10px', backgroundColor: '#fff3e0', borderRadius: '4px', fontSize: '12px' }}>Sem Sulfato</span>}
                    {selectedProduct.claim_sem_parabenos && <span style={{ padding: '4px 10px', backgroundColor: '#fce4ec', borderRadius: '4px', fontSize: '12px' }}>Sem Parabenos</span>}
                    {selectedProduct.claim_vegano && <span style={{ padding: '4px 10px', backgroundColor: '#e8f5e9', borderRadius: '4px', fontSize: '12px' }}>Vegano</span>}
                    {selectedProduct.claim_cruelty_free && <span style={{ padding: '4px 10px', backgroundColor: '#e1f5fe', borderRadius: '4px', fontSize: '12px' }}>Cruelty Free</span>}
                    {selectedProduct.claim_low_poo && <span style={{ padding: '4px 10px', backgroundColor: '#f3e5f5', borderRadius: '4px', fontSize: '12px' }}>Low Poo</span>}
                    {selectedProduct.claim_no_poo && <span style={{ padding: '4px 10px', backgroundColor: '#ede7f6', borderRadius: '4px', fontSize: '12px' }}>No Poo</span>}
                    {selectedProduct.claim_organico && <span style={{ padding: '4px 10px', backgroundColor: '#dcedc8', borderRadius: '4px', fontSize: '12px' }}>Organico</span>}
                    {selectedProduct.claim_natural && <span style={{ padding: '4px 10px', backgroundColor: '#c8e6c9', borderRadius: '4px', fontSize: '12px' }}>Natural</span>}
                    {!selectedProduct.claims_list && <span style={{ color: '#999', fontSize: '13px' }}>Nenhum claim detectado</span>}
                  </div>
                </div>
              </div>
            </div>
          </div>
        )}
          </>
        )}
      </div>
    </div>
  );
};

export default App;
