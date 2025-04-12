import React from 'react';
import { X } from 'lucide-react';

export default function FilterPanel() {
  return (
    <div className="bg-white rounded-lg shadow-lg p-6 mb-8">
      <div className="flex justify-between items-center mb-6">
        <h3 className="text-lg font-medium text-gray-900">Filter Candidates</h3>
        <button className="text-gray-400 hover:text-gray-500">
          <X className="w-5 h-5" />
        </button>
      </div>
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-2">
            Experience
          </label>
          <select className="w-full border border-gray-300 rounded-lg px-3 py-2">
            <option>Any</option>
            <option>0-2 years</option>
            <option>2-5 years</option>
            <option>5+ years</option>
          </select>
        </div>
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-2">
            Skills
          </label>
          <select className="w-full border border-gray-300 rounded-lg px-3 py-2">
            <option>Select skills</option>
            <option>React</option>
            <option>TypeScript</option>
            <option>Node.js</option>
          </select>
        </div>
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-2">
            Education
          </label>
          <select className="w-full border border-gray-300 rounded-lg px-3 py-2">
            <option>Any</option>
            <option>Bachelor's</option>
            <option>Master's</option>
            <option>PhD</option>
          </select>
        </div>
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-2">
            Status
          </label>
          <select className="w-full border border-gray-300 rounded-lg px-3 py-2">
            <option>All</option>
            <option>New</option>
            <option>Shortlisted</option>
            <option>Rejected</option>
          </select>
        </div>
      </div>
      <div className="mt-6 flex justify-end space-x-4">
        <button className="px-4 py-2 border border-gray-300 rounded-lg text-gray-700 hover:bg-gray-50">
          Reset
        </button>
        <button className="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700">
          Apply Filters
        </button>
      </div>
    </div>
  );
}