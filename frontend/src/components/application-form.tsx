import { useState } from 'react';
import { useForm } from 'react-hook-form';
import axios from 'axios';
import countries from 'country-telephone-data';

interface ApplicationFormProps {
  jobId: string;
  onSuccess: () => void;
}

export default function ApplicationForm({ jobId, onSuccess }: ApplicationFormProps) {
  const { 
    register, 
    handleSubmit, 
    formState: { errors, isSubmitting } 
  } = useForm();
  const [countrySearch, setCountrySearch] = useState('');
  const [selectedCode, setSelectedCode] = useState('+91');
  const [submitError, setSubmitError] = useState('');
  const sortedCountries = countries.allCountries.sort((a, b) => a.name.localeCompare(b.name));
  const filteredCountries = sortedCountries.filter(c => 
    c.name.toLowerCase().includes(countrySearch.toLowerCase()) ||
    c.iso2.includes(countrySearch.toUpperCase()) ||
    c.dialCode.includes(countrySearch)
  );

  const uploadResume = async (file: File) => {
    const { data } = await axios.get('http://localhost:5000/api/s3-presigned-url', {
      params: { fileName: file.name, fileType: file.type }
    });
    
    await axios.put(data.url, file, {
      headers: { 'Content-Type': file.type }
    });
    
    return data.key;
  };

  const onSubmit = async (formData: any) => {
    try {
      setSubmitError('');
      const s3Key = await uploadResume(formData.resume[0]);
      const fullPhone = `${selectedCode} ${formData.phone.replace(/[-\s]/g, '')}`;
      
      const response = await axios.post('http://localhost:5000/api/apply', {
        firstName: formData.firstName.trim(),
        lastName: formData.lastName.trim(),
        email: formData.email.toLowerCase().trim(),
        phone: fullPhone,
        jobPost: jobId,
        s3FileKey: s3Key,
        immediateJoiner: Boolean(formData.immediateJoiner),
        experience: Number(formData.experience)
      });
      
      onSuccess();
    } catch (error: any) {
      console.error('Application failed:', error);
      
      if (error.response?.data?.isDuplicate) {
        setSubmitError('You have already applied for this position');
      } else {
        setSubmitError('Failed to submit application. Please try again.');
      }
    }
  };

  return (
    <form onSubmit={handleSubmit(onSubmit)} className="space-y-4 p-4">
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        <div>
          <label className="block text-sm font-medium mb-1">First Name *</label>
          <input 
            {...register('firstName', { required: 'First name is required' })} 
            className="w-full p-2 border rounded-md"
          />
          {errors.firstName && <span className="text-red-500 text-sm">{(errors.firstName as any).message}</span>}
        </div>
        <div>
          <label className="block text-sm font-medium mb-1">Last Name *</label>
          <input 
            {...register('lastName', { required: 'Last name is required' })} 
            className="w-full p-2 border rounded-md"
          />
          {errors.lastName && <span className="text-red-500 text-sm">{(errors.lastName as any).message}</span>}
        </div>
      </div>

      <div>
        <label className="block text-sm font-medium mb-1">Email *</label>
        <input 
          type="email" 
          {...register('email', { 
            required: 'Email is required',
            pattern: {
              value: /^[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}$/i,
              message: 'Invalid email address'
            }
          })} 
          className="w-full p-2 border rounded-md"
        />
        {errors.email && <span className="text-red-500 text-sm">{(errors.email as any).message}</span>}
      </div>

      <div>
        <label className="block text-sm font-medium mb-1">Phone *</label>
        <div className="grid grid-cols-12 gap-3">
          <div className="col-span-12 md:col-span-4 relative">
            <div className="border rounded-md bg-white">
              <input
                type="text"
                placeholder="🔍 Search country..."
                className="w-full p-2 border-b text-sm"
                value={countrySearch}
                onChange={(e) => setCountrySearch(e.target.value)}
              />
              <select
                className="w-full p-2 text-sm appearance-none bg-transparent h-10"
                value={selectedCode}
                onChange={(e) => {
                  setSelectedCode(e.target.value);
                  setCountrySearch('');
                }}
              >
                {filteredCountries.map(c => (
                  <option key={c.iso2} value={c.dialCode}>
                    {c.name} ({c.dialCode})
                  </option>
                ))}
              </select>
            </div>
            {filteredCountries.length === 0 && (
              <div className="p-2 text-sm text-gray-500 bg-white border rounded-b-md">No matching countries</div>
            )}
          </div>
          
          <div className="col-span-12 md:col-span-8">
            <input
              type="tel"
              {...register('phone', {
                required: 'Phone number is required',
                pattern: {
                  value: /^[0-9\s-]{7,}$/,
                  message: "Invalid phone number format"
                }
              })}
              className="w-full p-2 border rounded-md"
              placeholder="1234567890"
            />
            {errors.phone && <span className="text-red-500 text-sm">{(errors.phone as any).message}</span>}
          </div>
        </div>
      </div>

      <div>
        <label className="block text-sm font-medium mb-1">Experience (years) *</label>
        <input 
          type="number" 
          {...register('experience', {
            required: 'Experience is required',
            min: { value: 0, message: 'Minimum 0 years' },
            max: { value: 99, message: 'Maximum 99 years' },
            valueAsNumber: true
          })} 
          className="w-full p-2 border rounded-md"
        />
        {errors.experience && <span className="text-red-500 text-sm">{(errors.experience as any).message}</span>}
      </div>

      <div>
        <label className="block text-sm font-medium mb-1">Resume (PDF) *</label>
        <input
          type="file"
          {...register('resume', { 
            required: 'Resume is required',
            validate: {
              pdfFormat: files => 
                files?.[0]?.type === 'application/pdf' || 'Only PDF files are allowed'
            }
          })}
          className="w-full p-2 border rounded-md"
          accept="application/pdf"
        />
        {errors.resume && <span className="text-red-500 text-sm">{(errors.resume as any).message}</span>}
      </div>

      <div className="flex items-center">
        <input 
          type="checkbox" 
          {...register('immediateJoiner')} 
          className="mr-2"
          id="immediateJoiner"
        />
        <label htmlFor="immediateJoiner" className="text-sm font-medium">
          Immediate Joiner
        </label>
      </div>

      <button
        type="submit"
        disabled={isSubmitting}
        className="w-full bg-blue-600 text-white p-2 rounded-md hover:bg-blue-700 disabled:bg-gray-400 transition-colors"
      >
        {isSubmitting ? 'Submitting...' : 'Submit Application'}
      </button>
    </form>
  );
}