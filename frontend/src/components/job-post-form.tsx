import { useForm } from 'react-hook-form';

interface JobPostFormProps {
  onSubmit: (data: any) => Promise<void>;
}

export default function JobPostForm({ onSubmit }: JobPostFormProps) {
  const { register, handleSubmit, formState: { isSubmitting }, } = useForm();

  return (
    <form onSubmit={handleSubmit(onSubmit)} className="space-y-4">
      <div>
        <label className="block text-sm font-medium text-gray-700">Job Title</label>
        <input
          {...register('title', { required: true })}
          className="mt-1 block p-2 w-full rounded-md border-gray-300 shadow-sm focus:border-purple-500 focus:ring-purple-500"
        />
      </div>
      <div>
        <label className="block text-sm font-medium text-gray-700">Location</label>
        <input
          {...register('location', { required: true })}
          className="mt-1 block p-2 w-full rounded-md border-gray-300 shadow-sm focus:border-purple-500 focus:ring-purple-500"
        />
      </div>
      <div>
        <label className="block text-sm font-medium text-gray-700">Job Type</label>
        <select
          {...register('jobType', { required: true })}
          className="mt-1 block w-full p-2 rounded-md border-gray-300 shadow-sm focus:border-purple-500 focus:ring-purple-500"
        >
          <option value="full-time">On-Site</option>
          <option value="part-time">Remote</option>
          <option value="contract">Hybrid</option>
        </select>
      </div>

      <div>
        <label className="block text-sm font-medium text-gray-700">Description</label>
        <textarea
          {...register('description', { required: true })}
          rows={4}
          className="mt-1 block w-full p-2 rounded-md border-gray-300 shadow-sm focus:border-purple-500 focus:ring-purple-500"
        />
      </div>

      <div>
        <label className="block text-sm font-medium text-gray-700">Number Of Openings</label>
        <input
          {...register('noOfOpenings', { min:1, max:99,required: true })}
          type="number"
          className="mt-1 block p-2 w-full rounded-md border-gray-300 shadow-sm focus:border-purple-500 focus:ring-purple-500"
        />
      </div>

      <div>
        <label className="block text-sm font-medium text-gray-700">Deadline</label>
        <input
          type="date"
          {...register('deadline', { required: true })}
          min={new Date().toISOString().split('T')[0]}
          className="mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-purple-500 focus:ring-purple-500"
        />
      </div>

      <button
        type="submit"
        disabled={isSubmitting}
        className="w-full bg-purple-600 text-white px-4 py-2 rounded-md hover:bg-purple-700 disabled:bg-purple-400"
      >
        {isSubmitting ? 'Creating...' : 'Create Job Post'}
      </button>
    </form>
  );
}