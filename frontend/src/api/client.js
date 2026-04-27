import axios from 'axios';

const API_BASE_URL = 'http://localhost:8000';

export const processDocument = async (file, userQuery) => {
    const formData = new FormData();
    formData.append('file', file);
    formData.append('user_query', userQuery);
    formData.append('mode', 'summary'); // Graph will decide, but we pass a default

    try {
        const response = await axios.post(`${API_BASE_URL}/process/`, formData, {
            headers: {
                'Content-Type': 'multipart/form-data',
            },
        });
        return response.data;
    } catch (error) {
        console.error('API Error:', error);
        throw new Error(error.response?.data?.error || error.message || 'Unknown system error');
    }
};
